import socket
import psutil
import pickle
import time
import select
import sys
import subprocess
import os

class TaskManager:
    def __init__(self):
        self.process = None
        self.task_id = None

    def start_task(self, task_id, script_path):
        if self.process and self.process.poll() is None:
            return False, "Task already running"

        try:
            # Run with -u for unbuffered output to capture prints immediately
            self.process = subprocess.Popen(
                [sys.executable, '-u', script_path], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            self.task_id = task_id
            # Set non-blocking
            os.set_blocking(self.process.stdout.fileno(), False)
            os.set_blocking(self.process.stderr.fileno(), False)
            return True, "Task started"
        except Exception as e:
            return False, str(e)

    def stop_task(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            self.task_id = None
            return True
        return False

    def is_running(self):
        return self.process and self.process.poll() is None

def get_system_stats():
    """
    Collects CPU and RAM utilization percentages.
    """
    return {
        "cpu": psutil.cpu_percent(interval=None), # Blocking interval causes issues in select loop
        "ram": psutil.virtual_memory().percent
    }

def main():
    """
    Main function to connect to the master server and send data.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Cluster Sentinel Agent")
    parser.add_argument('--host', type=str, default='127.0.0.1', help="Master server hostname or IP")
    parser.add_argument('--port', type=int, default=5000, help="Master server port")
    args = parser.parse_args()

    master_host = args.host
    master_port = args.port

    task_manager = TaskManager()

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((master_host, master_port))
                print(f"Connected to master server at {master_host}:{master_port}.")

                last_heartbeat = 0
                heartbeat_interval = 2.0

                while True:
                    inputs = [s]
                    if task_manager.is_running():
                        inputs.append(task_manager.process.stdout)
                        inputs.append(task_manager.process.stderr)

                    # Timeout allows us to send heartbeats
                    readable, _, _ = select.select(inputs, [], [], 1.0)

                    current_time = time.time()

                    # 1. Handle Incoming Data from Master
                    if s in readable:
                        data = s.recv(4096)
                        if not data:
                            print("Master closed connection.")
                            break
                        
                        try:
                            message = pickle.loads(data)
                            msg_type = message.get('type')
                            
                            if msg_type == 'EXECUTE':
                                tid = message['payload']['task_id']
                                script = message['payload']['script']
                                print(f"Received EXECUTE command: {script} (ID: {tid})")
                                success, msg = task_manager.start_task(tid, script)
                                s.sendall(pickle.dumps({
                                    'type': 'TASK_STATUS',
                                    'payload': {'task_id': tid, 'status': 'STARTED' if success else 'FAILED', 'info': msg}
                                }))

                            elif msg_type == 'STOP_TASK':
                                print("Received STOP_TASK command.")
                                stopped = task_manager.stop_task()
                                s.sendall(pickle.dumps({
                                    'type': 'TASK_STATUS',
                                    'payload': {'status': 'STOPPED' if stopped else 'NO_TASK'}
                                }))

                            elif msg_type == 'END':
                                print("Received END command. Exiting...")
                                task_manager.stop_task()
                                return

                        except Exception as e:
                            print(f"Error processing message: {e}")

                    # 2. Handle Task Output
                    if task_manager.is_running():
                        # STDOUT
                        if task_manager.process.stdout in readable:
                            line = task_manager.process.stdout.readline()
                            if line:
                                s.sendall(pickle.dumps({
                                    'type': 'TASK_RESULT',
                                    'payload': {'task_id': task_manager.task_id, 'data': line.strip(), 'stream': 'stdout'}
                                }))
                        # STDERR
                        if task_manager.process.stderr in readable:
                            line = task_manager.process.stderr.readline()
                            if line:
                                s.sendall(pickle.dumps({
                                    'type': 'TASK_RESULT',
                                    'payload': {'task_id': task_manager.task_id, 'data': line.strip(), 'stream': 'stderr'}
                                }))

                    # 3. Handle Heartbeat
                    if current_time - last_heartbeat >= heartbeat_interval:
                        stats = get_system_stats()
                        msg = {'type': 'HEARTBEAT', 'payload': stats}
                        s.sendall(pickle.dumps(msg))
                        print(f"[Heartbeat] CPU: {stats['cpu']}% RAM: {stats['ram']}%") 
                        last_heartbeat = current_time

        except ConnectionRefusedError:
            print("Connection refused. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
