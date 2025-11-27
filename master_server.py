# master_server.py

import socket
import pickle
import multiprocessing
import struct
import time
import threading
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

def handle_client(conn, addr, shm, lock):
    """Handles a single agent connection."""
    print(f"[Collector] Connected by {addr}")
    # Prepare address string for shared memory
    addr_str = str(addr)
    addr_bytes = addr_str.encode('utf-8')

    slot_index = None
    try:
        with lock:
            slot_index = find_slot(shm)

        if slot_index is None:
            print("[Collector] No available slots for new client.")
            return

        print(f"[Collector] Client {addr} assigned to slot {slot_index}")
        offset = slot_index * PACKED_DATA_SIZE

        # Set a timeout. If no data received in 5 seconds, assume dead.
        conn.settimeout(5.0)

        while True:
            try:
                data = conn.recv(4096)
                if not data:
                    break

                stats = pickle.loads(data)
                print(f"[Collector] Received from {addr}: {stats}")

                cpu = stats.get('cpu', 0.0)
                ram = stats.get('ram', 0.0)

                with lock:
                    # slot_index + 1 = Active ID (to avoid 0), addr_bytes, cpu, ram
                    packed_data = struct.pack(SHARED_MEM_FORMAT, slot_index + 1, addr_bytes, cpu, ram)
                    shm.buf[offset:offset + PACKED_DATA_SIZE] = packed_data

            except socket.timeout:
                print(f"[Collector] Client {slot_index+1} at {addr} timed out.")
                break
            except (pickle.UnpicklingError, EOFError):
                print(f"[Collector] Could not decode data from {addr}. Raw: {data}")

    except ConnectionResetError:
        print(f"[Collector] Connection reset by {addr}.")
    except Exception as e:
        print(f"[Collector] Error handling client {addr}: {e}")
    finally:
        # Clear the slot on disconnect
        if slot_index is not None:
            with lock:
                offset = slot_index * PACKED_DATA_SIZE
                # 0 = Inactive
                clear_data = struct.pack(SHARED_MEM_FORMAT, 0, b'', 0.0, 0.0)
                shm.buf[offset:offset + PACKED_DATA_SIZE] = clear_data
            print(f"[Collector] Cleared slot {slot_index}")

        print(f"[Collector] Client {addr} disconnected.")
        conn.close()


def collector_process_target(shm_name, lock, host, port):
    """Listens for agents and writes data to shared memory."""
    print("[Collector] Process started.")
    shm = shared_memory.SharedMemory(name=shm_name)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            s.listen()
            print(f"[Collector] Listening on {host}:{port}")

            while True:
                conn, addr = s.accept()
                # Use threading for better performance with I/O-bound tasks
                client_thread = threading.Thread(target=handle_client, args=(conn, addr, shm, lock))
                client_thread.start()
        except Exception as e:
            print(f"[Collector] Critical Error: {e}")


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
                                <h2>CPU Usage: {cpu:.2f}% (Client {slot_id}: {client_addr})</h2>
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

# --- Main Application ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cluster Sentinel Master Server")
    parser.add_argument('--host', type=str, default=DEFAULT_COLLECTOR_HOST, help="Collector bind host (default: 0.0.0.0)")
    parser.add_argument('--port', type=int, default=DEFAULT_COLLECTOR_PORT, help="Collector bind port (default: 13579)")
    args = parser.parse_args()

    shm = None
    shm_created = False
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
        collector = multiprocessing.Process(target=collector_process_target, args=(SHARED_MEM_NAME, lock, args.host, args.port))
        dashboard = multiprocessing.Process(target=dashboard_process_target, args=(SHARED_MEM_NAME, lock))

        collector.start()
        dashboard.start()

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
