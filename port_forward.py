import socket
import threading
import argparse
import sys

def forward(source, destination, description):
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break
            destination.sendall(data)
    except Exception as e:
        # Connection drops are normal, just exit the thread
        pass
    finally:
        source.close()
        destination.close()

def handle_client(client_socket, target_host, target_port):
    target_socket = None
    try:
        # Connect to the SSH tunnel endpoint (localhost:13579)
        target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_socket.connect((target_host, target_port))

        # Create bidirectional forwarding
        # Client -> Bridge -> Tunnel
        t1 = threading.Thread(target=forward, args=(client_socket, target_socket, "Client->Tunnel"))
        # Tunnel -> Bridge -> Client
        t2 = threading.Thread(target=forward, args=(target_socket, client_socket, "Tunnel->Client"))

        t1.start()
        t2.start()
    except Exception as e:
        print(f"[!] Failed to connect to tunnel target {target_host}:{target_port}: {e}")
        if client_socket: client_socket.close()
        if target_socket: target_socket.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Python Port Bridge (Socat alternative)")
    # The address that Compute Nodes will talk to (0.0.0.0)
    parser.add_argument('--host', type=str, default='0.0.0.0', help="Bind host (default: 0.0.0.0)")
	# The port the Compute Nodes will talk to (13580)
    parser.add_argument('--local-port', type=int, default=13580, help="Public port to listen on (e.g., 13580)")
    # The port the SSH Tunnel is listening on (13579)
    parser.add_argument('--remote-port', type=int, default=13579, help="Target port (SSH Tunnel end, e.g., 13579)")

    args = parser.parse_args()

    BIND_HOST = args.host  # Listen on all interfaces so Compute Nodes can reach us
    TARGET_HOST = '127.0.0.1' # Forward to localhost where SSH tunnel lives

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((BIND_HOST, args.local_port))
        server.listen(10)
        print(f"[*] Bridge Active: Listening on {BIND_HOST}:{args.local_port}")
        print(f"[*] Forwarding to: {TARGET_HOST}:{args.remote_port}")
        print("[*] Ready for connections...")

        while True:
            client_socket, addr = server.accept()
            print(f"[*] Incoming connection from {addr[0]}:{addr[1]}")
            threading.Thread(target=handle_client, args=(client_socket, TARGET_HOST, args.remote_port)).start()

    except KeyboardInterrupt:
        print("\n[*] Shutting down bridge.")
    except Exception as e:
        print(f"\n[!] Critical Error: {e}")
    finally:
        server.close()
