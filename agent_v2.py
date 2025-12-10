import socket
import psutil
import pickle
import time
import select
import sys
import os
import struct
import importlib.util
import threading
import queue
import traceback

# --- Security Configuration ---
# Maps task names to file paths
TASK_REGISTRY = {
    "crack": "tasks/cracker_task.py",
    "dummy": "tasks/dummy_task.py"
}
# ------------------------------

# --- Network Helper Functions (Framing) ---
def send_msg(sock, msg):
    """Prefix each message with a 4-byte big-endian unsigned integer"""
    data = pickle.dumps(msg)
    try:
        sock.sendall(struct.pack('>I', len(data)) + data)
    except (BrokenPipeError, ConnectionResetError):
        pass # Handle disconnects gracefully

def recv_msg(sock):
    """Read message length and unpack it into an integer, then read payload"""
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    return recvall(sock, msglen)

def recvall(sock, n):
    """Helper function to recv n bytes or return None if EOF is hit"""
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

# --- Threaded Task Manager ---
class TaskThread(threading.Thread):
    def __init__(self, task_id, script_path, args, result_queue):
        super().__init__()
        self.task_id = task_id
        self.script_path = script_path
        self.args = args
        self.result_queue = result_queue
        self._stop_event = threading.Event()

    def run(self):
        try:
            # 1. Load module dynamically
            spec = importlib.util.spec_from_file_location("dynamic_task", self.script_path)
            if not spec or not spec.loader:
                raise ImportError(f"Could not load task from {self.script_path}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 2. Check for 'run' function
            if not hasattr(module, 'run'):
                raise AttributeError("Task module must have a 'run(args, stop_event, result_queue)' function.")

            # 3. Execute 'run'
            # We pass the stop_event so the task can check if it should cancel itself
            module.run(self.args, self._stop_event, self.result_queue)
            
            self.result_queue.put({"type": "TASK_STATUS", "payload": {"task_id": self.task_id, "status": "COMPLETED"}})

        except Exception as e:
            traceback.print_exc()
            self.result_queue.put({"type": "TASK_STATUS", 
                                   "payload": {"task_id": self.task_id, "status": "ERROR", "info": str(e)}})

    def stop(self):
        self._stop_event.set()


class TaskManager:
    def __init__(self):
        self.current_thread = None
        self.current_task_id = None
        self.result_queue = queue.Queue()

    def start_task(self, task_id, task_name, args):
        if self.current_thread and self.current_thread.is_alive():
            return False, "Task already running"

        script_path = TASK_REGISTRY.get(task_name)
        if not script_path:
            return False, f"Unauthorized task: {task_name}"
        
        if not os.path.exists(script_path):
             return False, f"Script not found: {script_path}"

        try:
            # Create and start the thread
            self.current_thread = TaskThread(task_id, script_path, args, self.result_queue)
            self.current_task_id = task_id
            self.current_thread.start()
            return True, f"Task '{task_name}' started (Threaded)"
        except Exception as e:
            return False, str(e)

    def stop_task(self):
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread.stop()
            # We don't join() here to avoid blocking the main loop. 
            # The thread is expected to exit soon after checking stop_event.
            return True
        return False

    def is_running(self):
        return self.current_thread and self.current_thread.is_alive()


def get_system_stats():
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "ram": psutil.virtual_memory().percent
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Cluster Sentinel Agent V2")
    parser.add_argument('--host', type=str, default='127.0.0.1', help="Master server IP")
    parser.add_argument('--port', type=int, default=5000, help="Master server port")
    args = parser.parse_args()

    task_manager = TaskManager()

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((args.host, args.port))
                print(f"Connected to master server at {args.host}:{args.port}.")

                last_heartbeat = 0
                heartbeat_interval = 2.0

                while True:
                    # We monitor the socket for reading.
                    # We check the task result queue explicitly (since it's not a file descriptor, select won't work on it directly)
                    inputs = [s]
                    
                    readable, _, _ = select.select(inputs, [], [], 0.1) # Short timeout for responsiveness

                    current_time = time.time()

                    # 1. Handle Incoming Commands
                    if s in readable:
                        data = recv_msg(s) # Use framing
                        if not data:
                            print("Master closed connection.")
                            break
                        
                        try:
                            message = pickle.loads(data)
                            msg_type = message.get('type')
                            
                            if msg_type == 'EXECUTE':
                                tid = message['payload']['task_id']
                                task_name = message['payload']['task_name']
                                t_args = message['payload'].get('args', [])
                                
                                print(f"Received EXECUTE: {task_name} {t_args}")
                                success, msg = task_manager.start_task(tid, task_name, t_args)
                                send_msg(s, {
                                    'type': 'TASK_STATUS', 
                                    'payload': {'task_id': tid, 'status': 'STARTED' if success else 'FAILED', 'info': msg}
                                })

                            elif msg_type == 'STOP_TASK':
                                print("Received STOP_TASK.")
                                stopped = task_manager.stop_task()
                                send_msg(s, {
                                    'type': 'TASK_STATUS',
                                    'payload': {'status': 'STOPPING' if stopped else 'NO_TASK'}
                                })
                            
                            elif msg_type == 'END':
                                task_manager.stop_task()
                                return

                        except Exception as e:
                            print(f"Error processing message: {e}")

                    # 2. Handle Task Results (Queue)
                    # Drain the queue so we don't lag behind
                    while not task_manager.result_queue.empty():
                        result = task_manager.result_queue.get()
                        # If the task emits raw strings, wrap them. If it emits dicts, send them.
                        # We expect tasks to emit dicts like {"type": "TASK_RESULT", "payload": ...}
                        # But for safety, we can wrap raw data.
                        if isinstance(result, str):
                             send_msg(s, {'type': 'TASK_RESULT', 'payload': {'task_id': task_manager.current_task_id, 'data': result}})
                        elif isinstance(result, dict):
                             # Ensure task_id is present
                             if 'payload' in result and 'task_id' not in result['payload']:
                                 result['payload']['task_id'] = task_manager.current_task_id
                             send_msg(s, result)

                    # 3. Handle Heartbeat
                    if current_time - last_heartbeat >= heartbeat_interval:
                        stats = get_system_stats()
                        send_msg(s, {'type': 'HEARTBEAT', 'payload': stats})
                        last_heartbeat = current_time

        except ConnectionRefusedError:
            print("Connection refused. Retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    main()
