import time

def run(args, stop_event, result_queue):
    for i in range(1, 100000):
        if stop_event.is_set():
            result_queue.put("Dummy task stopped.")
            break
        result_queue.put(f"Working... ({i})")
        time.sleep(5)

if __name__ == "__main__":
    import queue, threading
    q = queue.Queue()
    evt = threading.Event()
    run([], evt, q)