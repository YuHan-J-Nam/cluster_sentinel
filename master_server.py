# master_server.py

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
# Defaults
DEFAULT_COLLECTOR_HOST = '0.0.0.0'
DEFAULT_COLLECTOR_PORT = 13579
DASHBOARD_HOST = '127.0.0.1'
DASHBOARD_PORT = 8080

SHARED_MEM_NAME = 'cluster_sentinel_shm'
MAX_CLIENTS = 10
# slot_id (int), address (string 64 bytes), cpu (float), ram (float)
SHARED_MEM_FORMAT = 'i64sff'
PACKED_DATA_SIZE = struct.calcsize(SHARED_MEM_FORMAT)
SHARED_MEM_SIZE = PACKED_DATA_SIZE * MAX_CLIENTS


# --- Collector Process ---

def find_slot(shm):
    """Finds an empty slot in shared memory."""
    for i in range(MAX_CLIENTS):
        offset = i * PACKED_DATA_SIZE
        slot_id, _, _, _ = struct.unpack(SHARED_MEM_FORMAT, shm.buf[offset:offset + PACKED_DATA_SIZE])
        if slot_id == 0:
            return i
    return None

def handle_client(conn, addr, shm, lock, client_data, slot_index):
    """Handles a single agent connection."""
    print(f"[Collector] Connected by {addr}")
    # Prepare address string for shared memory
    addr_str = str(addr)
    addr_bytes = addr_str.encode('utf-8')

    # Extract client-specific data
    my_queue = client_data['queue']
    pipe_r = client_data['pipe_r']
    pipe_w = client_data['pipe_w'] # pipe_w is technically not used here, but kept for reference

    try:
        # The slot is already reserved and assigned in collector_process_target
        print(f"[Collector] Client {addr} assigned to slot {slot_index}")
        offset = slot_index * PACKED_DATA_SIZE
        
        # Track last activity for timeout (heartbeats are every 2s)
        last_active = time.time()
        CLIENT_TIMEOUT = 6.0 # seconds

        while True:
            # Calculate dynamic timeout for select
            timeout_duration = CLIENT_TIMEOUT - (time.time() - last_active)
            if timeout_duration < 0:
                print(f"[Collector] Client {addr} timed out (no data for {CLIENT_TIMEOUT}s).")
                break
            
            inputs = [conn, pipe_r] # Add the pipe read end to select inputs

            # Select loop to handle both socket and pipe
            readable, _, _ = select.select(inputs, [], [], timeout_duration)

            # Handle pipe readability - means a command was put in the queue
            if pipe_r in readable:
                os.read(pipe_r, 1) # Read and discard the byte to clear the pipe

            # 1. Handle Incoming Data from Agent
            if conn in readable:
                try:
                    data = conn.recv(4096)
                    last_active = time.time() # Reset timeout on any data
                except ConnectionResetError:
                    print(f"[Collector] Connection reset by {addr} (recv).")
                    break

                if not data:
                    print(f"[Collector] {addr} closed connection (EOF).")
                    break

                try:
                    message = pickle.loads(data)
                    msg_type = message.get('type')
                    
                    if msg_type == 'HEARTBEAT':
                        stats = message.get('payload', {})
                        cpu = stats.get('cpu', 0.0)
                        ram = stats.get('ram', 0.0)

                        with lock:
                            # Update existing slot
                            try:
                                packed_data = struct.pack(SHARED_MEM_FORMAT, slot_index + 1, addr_bytes, cpu, ram)
                                shm.buf[offset:offset + PACKED_DATA_SIZE] = packed_data
                                # print(f"[Collector] Updated heartbeat for slot {slot_index}") # Debug
                            except Exception as pack_err:
                                print(f"[Collector] Error packing data for slot {slot_index}: {pack_err}")
                    
                    elif msg_type == 'TASK_RESULT':
                        payload = message.get('payload', {})
                        tid = payload.get('task_id')
                        stream = payload.get('stream')
                        data_str = payload.get('data')
                        print(f"\n[Client {slot_index}][Task {tid}][{stream}] {data_str}")
                        
                    elif msg_type == 'TASK_STATUS':
                         print(f"\n[Client {slot_index}] Status: {message['payload']}")
                    
                    elif msg_type is None and isinstance(message, dict) and 'cpu' in message:
                         # Legacy Agent Detection
                         print(f"[Collector] WARNING: Client {addr} is running an old version of agent.py! Please update it.")

                except (pickle.UnpicklingError, EOFError) as e:
                    print(f"[Collector] Could not decode data from {addr}: {e}")

            # 2. Handle Outgoing Commands from Queue
            try:
                while True:
                    cmd = my_queue.get_nowait()
                    print(f"[Collector] Sending command to Client {slot_index}: {cmd['type']}")
                    try:
                        conn.sendall(pickle.dumps(cmd))
                    except (BrokenPipeError, ConnectionResetError):
                        print(f"[Collector] Failed to send command to {addr}: Connection lost.")
                        raise # Re-raise to trigger exception handler/finally
            except queue.Empty:
                pass

    except ConnectionResetError:
        print(f"[Collector] Connection reset by {addr}.")
    except Exception as e:
        print(f"[Collector] Error handling client {addr}: {e}")
    finally:
        # Clear the slot on disconnect
        if slot_index is not None:
            print(f"[Collector] Cleaning up slot {slot_index} for {addr}...")
            with lock:
                offset = slot_index * PACKED_DATA_SIZE
                # 0 = Inactive
                try:
                    clear_data = struct.pack(SHARED_MEM_FORMAT, 0, b'', 0.0, 0.0)
                    shm.buf[offset:offset + PACKED_DATA_SIZE] = clear_data
                    print(f"[Collector] SUCCESS: Cleared slot {slot_index} in shared memory.")
                except Exception as e:
                    print(f"[Collector] ERROR: Failed to clear slot {slot_index}: {e}")
        else:
             print(f"[Collector] Disconnect from {addr} (No slot assigned).")

        print(f"[Collector] Client {addr} disconnected.")
        conn.close()
        
        # Close the pipe read file descriptor for this client's thread
        if pipe_r is not None:
            os.close(pipe_r)
            print(f"[Collector] Closed pipe_r for slot {slot_index}")

def dispatcher_thread(master_cmd_queue, client_queues_data):
    """Reads global commands and routes them to specific client queues."""
    while True:
        try:
            # (slot_id, command_dict)
            target_slot, cmd = master_cmd_queue.get()
            if 0 <= target_slot < MAX_CLIENTS:
                # Get the specific client's queue and pipe_w from the data structure
                client_data = client_queues_data[target_slot]
                client_data['queue'].put(cmd)
                os.write(client_data['pipe_w'], b'1') # Wake up the client's handle_client thread
            else:
                print(f"[Dispatcher] Invalid slot ID: {target_slot}")
        except Exception as e:
            print(f"[Dispatcher] Error: {e}")

def collector_process_target(shm_name, lock, host, port, master_cmd_queue):
    """Listens for agents and writes data to shared memory."""
    print("[Collector] Process started.")
    shm = shared_memory.SharedMemory(name=shm_name)

    # Each slot now has a queue for commands and a pipe for waking up its handle_client thread
    client_data_per_slot = []
    for _ in range(MAX_CLIENTS):
        q = queue.Queue()
        r_fd, w_fd = os.pipe() # Create a pipe for self-pipe trick
        os.set_blocking(r_fd, False) # Make read end non-blocking
        client_data_per_slot.append({'queue': q, 'pipe_r': r_fd, 'pipe_w': w_fd})

    # Start Dispatcher, passing the list of client data dictionaries
    d_thread = threading.Thread(target=dispatcher_thread, args=(master_cmd_queue, client_data_per_slot), daemon=True)
    d_thread.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            s.listen()
            print(f"[Collector] Listening on {host}:{port}")

            while True:
                conn, addr = s.accept()
                
                slot_idx = None
                with lock: # Ensure exclusive access when finding and reserving slot
                    slot_idx = find_slot(shm)

                    if slot_idx is None:
                        print(f"[Collector] No available slots for new client {addr}. Closing connection.")
                        conn.close()
                        continue # Continue listening for new clients

                    # Immediately reserve the slot in shared memory
                    addr_str = str(addr)
                    addr_bytes = addr_str.encode('utf-8')
                    offset = slot_idx * PACKED_DATA_SIZE
                    packed_data = struct.pack(SHARED_MEM_FORMAT, slot_idx + 1, addr_bytes, 0.0, 0.0)
                    shm.buf[offset:offset + PACKED_DATA_SIZE] = packed_data
                    print(f"[Collector] Reserving slot {slot_idx} for {addr}")

                # Pass the specific client_data dictionary AND the assigned slot_idx
                client_thread = threading.Thread(target=handle_client, 
                                                args=(conn, addr, shm, lock, client_data_per_slot[slot_idx], slot_idx))
                client_thread.start()

        except Exception as e:
            print(f"[Collector] Critical Error: {e}")
        finally:
            # Close all pipe write FDs when the collector process exits
            for client_data in client_data_per_slot:
                os.close(client_data['pipe_w'])
            # handle_client threads are responsible for closing their pipe_r



# --- Dashboard Process ---

def dashboard_process_target(shm_name, lock):
    """Runs a simple web server to display stats from shared memory."""
    print("[Dashboard] Process started.")
    shm = shared_memory.SharedMemory(name=shm_name)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((DASHBOARD_HOST, DASHBOARD_PORT))
        s.listen()
        print(f"[Dashboard] Web server running at http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")

        while True:
            conn, addr = s.accept()
            with conn:
                clients_html = ""
                with lock:
                    for i in range(MAX_CLIENTS):
                        offset = i * PACKED_DATA_SIZE
                        packed_data = shm.buf[offset:offset + PACKED_DATA_SIZE]
                        slot_id, addr_bytes, cpu, ram = struct.unpack(SHARED_MEM_FORMAT, packed_data)

                        if slot_id != 0: # If the slot is active
                            # Decode bytes to string and strip null padding
                            client_addr = addr_bytes.decode('utf-8').strip('\x00')
                            clients_html += f"""
                            <div class="metric">
                                <h2>CPU Usage: {cpu:.2f}% (Client {slot_id-1} [Slot {i}]: {client_addr})</h2>
                                <div class="bar-container">
                                    <div class="bar cpu-bar" style="width: {cpu}%;">{cpu:.2f}%</div>
                                </div>
                            </div>
                            <div class="metric">
                                <h2>RAM Usage: {ram:.2f}%</h2>
                                <div class="bar-container">
                                    <div class="bar ram-bar" style="width: {ram}%;">{ram:.2f}%</div>
                                </div>
                            </div>
                            <hr>
                            """

                if not clients_html:
                    clients_html = "<p>No connected agents.</p>"

                # Generate HTML response
                html_content = f"""
                <html>
                <head>
                    <title>Cluster Sentinel</title>
                    <meta http-equiv="refresh" content="2">
                    <style>
                        body {{ font-family: 'Courier New', Courier, monospace; background-color: #0f0f0f; color: #00ff00; }}
                        .container {{ width: 80%; margin: 50px auto; border: 1px solid #00ff00; padding: 20px; }}
                        h1 {{ text-align: center; }}
                        .metric {{ margin: 20px 0; }}
                        .bar-container {{ width: 100%; background-color: #333; border: 1px solid #555; }}
                        .bar {{ height: 30px; text-align: center; line-height: 30px; color: #000; font-weight: bold; }}
                        .cpu-bar {{ background-color: #ff4500; }}
                        .ram-bar {{ background-color: #1e90ff; }}
                        hr {{ border: 1px solid #333; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Cluster Sentinel Dashboard</h1>
                        {clients_html}
                        <p style="text-align:center;">Page auto-refreshes every 2 seconds.</p>
                    </div>
                </body>
                </html>
                """

                # Send HTTP response
                response = f"HTTP/1.1 200 OK\nContent-Type: text/html\nContent-Length: {len(html_content)}\n\n{html_content}"
                conn.sendall(response.encode('utf-8'))

# --- Input Thread (CLI) ---

def input_thread_target(master_cmd_queue):
    """Reads stdin and sends commands to the collector."""
    print("--- Master CLI ---")
    print("Commands:")
    print("  exec <slot_id> <script_path>  - Execute a task")
    print("  stop <slot_id>                - Stop current task")
    print("  end <slot_id>                 - Terminate agent")
    print("------------------")
    
    while True:
        try:
            cmd_str = sys.stdin.readline()
            if not cmd_str:
                break
            cmd_str = cmd_str.strip()
            if not cmd_str:
                continue

            parts = cmd_str.split()
            command = parts[0].lower()

            if command == 'exec':
                if len(parts) < 3:
                    print("Usage: exec <slot_id> <script_path>")
                    continue
                try:
                    slot_id = int(parts[1])
                    script = parts[2]
                    task_id = str(uuid.uuid4())[:8]
                    msg = {
                        'type': 'EXECUTE',
                        'payload': {'task_id': task_id, 'script': script}
                    }
                    master_cmd_queue.put((slot_id, msg))
                    print(f"Queued EXECUTE for slot {slot_id}")
                except ValueError:
                    print("Invalid slot ID.")

            elif command == 'stop':
                if len(parts) < 2:
                    print("Usage: stop <slot_id>")
                    continue
                try:
                    slot_id = int(parts[1])
                    msg = {'type': 'STOP_TASK', 'payload': {}}
                    master_cmd_queue.put((slot_id, msg))
                    print(f"Queued STOP_TASK for slot {slot_id}")
                except ValueError:
                    print("Invalid slot ID.")

            elif command == 'end':
                if len(parts) < 2:
                    print("Usage: end <slot_id>")
                    continue
                try:
                    slot_id = int(parts[1])
                    msg = {'type': 'END', 'payload': {}}
                    master_cmd_queue.put((slot_id, msg))
                    print(f"Queued END for slot {slot_id}")
                except ValueError:
                    print("Invalid slot ID.")
            
            else:
                print("Unknown command.")

        except Exception as e:
            print(f"CLI Error: {e}")

# --- Main Application ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cluster Sentinel Master Server")
    parser.add_argument('--host', type=str, default=DEFAULT_COLLECTOR_HOST, help="Collector bind host (default: 0.0.0.0)")
    parser.add_argument('--port', type=int, default=DEFAULT_COLLECTOR_PORT, help="Collector bind port (default: 13579)")
    args = parser.parse_args()

    shm = None
    shm_created = False
    
    master_cmd_queue = multiprocessing.Queue()

    try:
        # Clean up old segment first
        try:
            # Attempt to link to an existing segment to unlink it
            existing_shm = shared_memory.SharedMemory(name=SHARED_MEM_NAME)
            existing_shm.close()
            existing_shm.unlink()
            print(f"Unlinked stale shared memory segment '{SHARED_MEM_NAME}'.")
        except FileNotFoundError:
            pass  # This is the normal case, nothing to do

        # Create shared memory and a lock
        shm = shared_memory.SharedMemory(name=SHARED_MEM_NAME, create=True, size=SHARED_MEM_SIZE)
        shm_created = True
        print(f"Created shared memory segment '{SHARED_MEM_NAME}' of size {SHARED_MEM_SIZE} bytes.")

        lock = Lock()

        # Initialize shared memory with zeros
        with lock:
            initial_data = struct.pack(SHARED_MEM_FORMAT, 0, b'', 0.0, 0.0)
            for i in range(MAX_CLIENTS):
                offset = i * PACKED_DATA_SIZE
                shm.buf[offset:offset + PACKED_DATA_SIZE] = initial_data

        # Create and start processes
        collector = multiprocessing.Process(target=collector_process_target, args=(SHARED_MEM_NAME, lock, args.host, args.port, master_cmd_queue))
        dashboard = multiprocessing.Process(target=dashboard_process_target, args=(SHARED_MEM_NAME, lock))

        collector.start()
        dashboard.start()

        # Start CLI thread in Main Process
        cli_thread = threading.Thread(target=input_thread_target, args=(master_cmd_queue,), daemon=True)
        cli_thread.start()

        # Wait for processes to finish (they won't, in this case, until interrupted)
        collector.join()
        dashboard.join()

    except KeyboardInterrupt:
        print("\nCaught KeyboardInterrupt, shutting down.")
    finally:
        # Clean up processes and shared memory
        if 'collector' in locals() and collector.is_alive():
            collector.terminate()
            collector.join()
        if 'dashboard' in locals() and dashboard.is_alive():
            dashboard.terminate()
            dashboard.join()

        if shm:
            shm.close()
            if shm_created:
                shm.unlink()
                print(f"Unlinked shared memory '{SHARED_MEM_NAME}'.")

        print("Shutdown complete.")
