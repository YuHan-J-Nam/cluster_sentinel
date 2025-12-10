import sys
import hashlib
import itertools

# Search space: a-z, A-Z, 0-9
CHARSET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

def crack(target_hash, start_char, end_char):
    try:
        start_idx = CHARSET.index(start_char)
        end_idx = CHARSET.index(end_char)
    except ValueError:
        print(f"Error: Start/End chars must be in set: {CHARSET}")
        sys.exit(1)

    print(f"Starting crack for range [{start_char}-{end_char}) against {target_hash[:8]}...")

    # Iterate through the first character based on the assigned range
    for i in range(start_idx, end_idx):
        first_char = CHARSET[i]
        
        # Report progress periodically (e.g., every new first character)
        print(f"Scanning prefix '{first_char}'...")

        # Generate the remaining 4 characters
        for p in itertools.product(CHARSET, repeat=4):
            candidate = first_char + "".join(p)
            
            # Check Hash
            if hashlib.sha256(candidate.encode()).hexdigest() == target_hash:
                print(f"FOUND: {candidate}")
                return

    print("DONE: Range exhausted with no match.")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python cracker_task.py <target_hash> <start_char> <end_char>")
        sys.exit(1)

    target_hash = sys.argv[1]
    start_char = sys.argv[2]
    end_char = sys.argv[3]

    crack(target_hash, start_char, end_char)
