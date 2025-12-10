import sys
import hashlib
import itertools

# Search space: a-z, A-Z, 0-9
CHARSET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

def run(args, stop_event, result_queue):
    """
    Args:
        args: list [target_hash, start_char, end_char]
        stop_event: threading.Event to check for cancellation
        result_queue: queue.Queue to send results back
    """
    if len(args) < 3:
        result_queue.put("Error: Missing arguments. Usage: <hash> <start> <end>")
        return

    target_hash = args[0]
    start_char = args[1]
    end_char = args[2]

    try:
        start_idx = CHARSET.index(start_char)
        end_idx = CHARSET.index(end_char)
    except ValueError:
        result_queue.put(f"Error: Start/End chars must be in set: {CHARSET}")
        return

    result_queue.put(f"Starting crack for range [{start_char}-{end_char}) against {target_hash[:8]}...")

    # Iterate through the first character based on the assigned range
    for i in range(start_idx, end_idx):
        if stop_event.is_set():
            result_queue.put("Task stopped by user.")
            return

        first_char = CHARSET[i]
        
        # Report progress periodically
        result_queue.put(f"Scanning prefix '{first_char}'...")

        # Generate the remaining 4 characters
        for p in itertools.product(CHARSET, repeat=4):
            # Check for stop signal more frequently if needed, but inner loop is fast
            if stop_event.is_set(): 
                return

            candidate = first_char + "".join(p)
            
            # Check Hash
            if hashlib.sha256(candidate.encode()).hexdigest() == target_hash:
                result_queue.put(f"FOUND: {candidate}")
                return

    result_queue.put("DONE: Range exhausted with no match.")

if __name__ == "__main__":
    # Keep CLI support for standalone testing
    import queue, threading
    if len(sys.argv) != 4:
        print("Usage: python cracker_task.py <target_hash> <start_char> <end_char>")
        sys.exit(1)

    q = queue.Queue()
    evt = threading.Event()
    run(sys.argv[1:], evt, q)
    while not q.empty():
        print(q.get())

