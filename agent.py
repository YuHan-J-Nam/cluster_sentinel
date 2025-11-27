import socket
import psutil
import pickle
import time

def get_system_stats():
    """
    Collects CPU and RAM utilization percentages.
    """
    return {
        "cpu": psutil.cpu_percent(interval=1),
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

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((master_host, master_port))
                print(f"Connected to master server at {master_host}:{master_port}.")

                while True:
                    stats = get_system_stats()
                    data = pickle.dumps(stats)
                    s.sendall(data)
                    print(f"Sent data: {stats}")
                    time.sleep(2)

        except ConnectionRefusedError:
            print("Connection refused. Master server might not be running. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"An error occurred: {e}")
            print("Attempting to reconnect in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()
