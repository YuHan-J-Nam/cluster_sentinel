import socket
import pickle
import multiprocessing
import struct
import time
import threading
import queue
import sys
import os
import select
import uuid
from multiprocessing import shared_memory, Lock

# --- Configuration ---
DEFAULT_COLLECTOR_HOST = '0.0.0.0'
DEFAULT_COLLECTOR_PORT = 13579
DASHBOARD_HOST = '127.0.0.1'
DASHBOARD_PORT = 8080
SHARED_MEM_NAME = 'cluster_sentinel_shm'
MAX_CLIENTS = 10
SHARED_MEM_FORMAT = 'i64sff'
PACKED_DATA_SIZE = struct.calcsize(SHARED_MEM_FORMAT)
SHARED_MEM_SIZE = PACKED_DATA_SIZE * MAX_CLIENTS

# --- Network Helper Functions (Framing) ---
def send_msg(sock, msg):
    """Prefix each message with a 4-byte big-endian unsigned integer"""
    data = pickle.dumps(msg)
    try:
        sock.sendall(struct.pack('>I', len(data)) + data)
    except (BrokenPipeError, ConnectionResetError):
        pass

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

# --- Collector Logic ---

def find_slot(shm):
    for i in range(MAX_CLIENTS):
        offset = i * PACKED_DATA_SIZE
        slot_id, _, _, _ = struct.unpack(SHARED_MEM_FORMAT, shm.buf[offset:offset + PACKED_DATA_SIZE])
        if slot_id == 0:
            return i
    return None

def handle_client(conn, addr, shm, lock, client_data, slot_index):
    print(f"[Collector] Connected by {addr}")
    addr_str = str(addr)
    addr_bytes = addr_str.encode('utf-8')
    my_queue = client_data['queue']
    pipe_r = client_data['pipe_r']

    try:
        print(f"[Collector] Client {addr} assigned to slot {slot_index}")
        offset = slot_index * PACKED_DATA_SIZE
        last_active = time.time()
        CLIENT_TIMEOUT = 10.0 # Increased timeout for stability

        while True:
            timeout_duration = CLIENT_TIMEOUT - (time.time() - last_active)
            if timeout_duration < 0:
                print(f"[Collector] Client {addr} timed out.")
                break
            
            inputs = [conn, pipe_r]
            readable, _, _ = select.select(inputs, [], [], timeout_duration)

            # 1. Handle Queue Command (Self-Pipe)
            if pipe_r in readable:
                os.read(pipe_r, 1) # Clear byte
                try:
                    while True:
                        cmd = my_queue.get_nowait()
                        print(f"[Collector] Sending {cmd['type']} to {slot_index}")
                        send_msg(conn, cmd) # Use framing
                except queue.Empty:
                    pass

            # 2. Handle Incoming Data
            if conn in readable:
                try:
                    data = recv_msg(conn) # Use framing!
                    last_active = time.time()
                except ConnectionResetError:
                    break

                if not data:
                    print(f"[Collector] {addr} closed connection.")
                    break

                try:
                    message = pickle.loads(data)
                    msg_type = message.get('type')
                    
                    if msg_type == 'HEARTBEAT':
                        stats = message.get('payload', {})
                        with lock:
                            packed_data = struct.pack(SHARED_MEM_FORMAT, slot_index + 1, addr_bytes, stats.get('cpu',0.0), stats.get('ram',0.0))
                            shm.buf[offset:offset + PACKED_DATA_SIZE] = packed_data
                    
                    elif msg_type == 'TASK_RESULT':
                        payload = message.get('payload', {})
                        print(f"\n[Client {slot_index}][Task {payload.get('task_id')}] {payload.get('data')}")
                        
                    elif msg_type == 'TASK_STATUS':
                         print(f"\n[Client {slot_index}] Status: {message['payload']}")

                except (pickle.UnpicklingError, EOFError) as e:
                    print(f"[Collector] Pickle Error: {e}")

    except Exception as e:
        print(f"[Collector] Error: {e}")
    finally:
        if slot_index is not None:
            with lock:
                offset = slot_index * PACKED_DATA_SIZE
                shm.buf[offset:offset + PACKED_DATA_SIZE] = struct.pack(SHARED_MEM_FORMAT, 0, b'', 0.0, 0.0)
        conn.close()
        os.close(pipe_r)

def dispatcher_thread(master_cmd_queue, client_queues_data):
    while True:
        try:
            target_slot, cmd = master_cmd_queue.get()
            if 0 <= target_slot < MAX_CLIENTS:
                client_data = client_queues_data[target_slot]
                client_data['queue'].put(cmd)
                os.write(client_data['pipe_w'], b'1')
        except Exception:
            pass

def collector_process_target(shm_name, lock, host, port, master_cmd_queue):
    shm = shared_memory.SharedMemory(name=shm_name)
    client_data_per_slot = []
    for _ in range(MAX_CLIENTS):
        q = queue.Queue()
        r_fd, w_fd = os.pipe()
        os.set_blocking(r_fd, False)
        client_data_per_slot.append({'queue': q, 'pipe_r': r_fd, 'pipe_w': w_fd})

    threading.Thread(target=dispatcher_thread, args=(master_cmd_queue, client_data_per_slot), daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen()
        print(f"[Collector V2] Listening on {host}:{port}")

        while True:
            conn, addr = s.accept()
            with lock:
                slot_idx = find_slot(shm)
                if slot_idx is not None:
                    offset = slot_idx * PACKED_DATA_SIZE
                    shm.buf[offset:offset + PACKED_DATA_SIZE] = struct.pack(SHARED_MEM_FORMAT, slot_idx + 1, str(addr).encode('utf-8'), 0.0, 0.0)
            
            if slot_idx is not None:
                threading.Thread(target=handle_client, args=(conn, addr, shm, lock, client_data_per_slot[slot_idx], slot_idx)).start()
            else:
                conn.close()

# --- Dashboard (Unchanged Logic, just simplified) ---
def dashboard_process_target(shm_name, lock):
    shm = shared_memory.SharedMemory(name=shm_name)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((DASHBOARD_HOST, DASHBOARD_PORT))
        s.listen()
        print(f"[Dashboard] http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
        while True:
            conn, _ = s.accept()
            with conn:
                clients_html = ""
                with lock:
                    for i in range(MAX_CLIENTS):
                        offset = i * PACKED_DATA_SIZE
                        slot_id, addr_bytes, cpu, ram = struct.unpack(SHARED_MEM_FORMAT, shm.buf[offset:offset + PACKED_DATA_SIZE])
                        if slot_id != 0:
                            clients_html += f"<div>Client {slot_id-1}: CPU {cpu:.1f}% | RAM {ram:.1f}%</div>"
                
                resp = f"HTTP/1.1 200 OK\nContent-Type: text/html\n\n<html><meta http-equiv='refresh' content='2'><body><h1>Cluster Sentinel V2</h1>{clients_html}</body></html>"
                conn.sendall(resp.encode())

# --- Input CLI ---
def input_thread_target(master_cmd_queue):
    print("--- V2 CLI: exec <slot> <task> [args] ---")
    while True:
        try:
            line = sys.stdin.readline()
            if not line: break
            parts = line.strip().split()
            if not parts: continue
            
            if parts[0] == 'exec':
                slot = int(parts[1])
                name = parts[2]
                args = parts[3:]
                master_cmd_queue.put((slot, {'type': 'EXECUTE', 'payload': {'task_id': str(uuid.uuid4())[:8], 'task_name': name, 'args': args}}))
                print(f"Sent EXECUTE {name} to {slot}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default=DEFAULT_COLLECTOR_HOST)
    parser.add_argument('--port', type=int, default=DEFAULT_COLLECTOR_PORT)
    args = parser.parse_args()

    master_cmd_queue = multiprocessing.Queue()
    
    # Init Shared Mem
    try:
        shm = shared_memory.SharedMemory(name=SHARED_MEM_NAME, create=True, size=SHARED_MEM_SIZE)
    except FileExistsError:
        shm = shared_memory.SharedMemory(name=SHARED_MEM_NAME)
    
    lock = Lock()

    p1 = multiprocessing.Process(target=collector_process_target, args=(SHARED_MEM_NAME, lock, args.host, args.port, master_cmd_queue))
    p2 = multiprocessing.Process(target=dashboard_process_target, args=(SHARED_MEM_NAME, lock))
    
    p1.start(); p2.start()
    threading.Thread(target=input_thread_target, args=(master_cmd_queue,), daemon=True).start()

    try:
        p1.join(); p2.join()
    except KeyboardInterrupt:
        p1.terminate(); p2.terminate()
        shm.close(); shm.unlink()
