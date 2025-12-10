# Implementation Plan: Distributed Hash Cracker (Secure)

**Goal:** Create a distributed system to crack a 5-character alphanumeric password, utilizing a **Whitelist Security Model** to prevent command injection.

## 1. Security Architecture: The Task Registry
To prevent arbitrary code execution, the Agent will no longer accept a "script path". Instead, it will accept a "Task Name".

**Agent Configuration:**
```python
# agent.py
TASK_REGISTRY = {
    "crack": "cracker_task.py",
    # "render": "fractal_renderer.py" (Future)
}
```

**Flow:**
1.  Master sends: `{"type": "EXECUTE", "task_name": "crack", "args": ["hash", "a", "m"]}`
2.  Agent checks `TASK_REGISTRY["crack"]`.
    *   **Found:** Resolves to `./cracker_task.py`.
    *   **Not Found:** Returns `{"status": "ERROR", "msg": "Unauthorized Task"}`.
3.  Agent executes: `subprocess.Popen([sys.executable, '-u', './cracker_task.py', 'hash', 'a', 'm'])`
    *   *Note:* `shell=False` is implied, rendering shell injection impossible.

## 2. The Task Script: `cracker_task.py`
This script performs the actual CPU-intensive work.

*   **Inputs (CLI Args):** `target_hash`, `start_char`, `end_char`.
*   **Logic:**
    1.  Generate all 5-char strings starting with characters between `start_char` and `end_char`.
    2.  Hash each string using `hashlib.sha256`.
    3.  Compare with `target_hash`.
    4.  Print `FOUND: <password>` if matched.

## 3. Required Code Changes

### A. `agent.py` (The Guard)
*   **Update `TaskManager.start_task`:**
    *   Accept `task_name` and `args` list instead of `script_path`.
    *   Implement the `TASK_REGISTRY` lookup.
    *   Pass `args` to `subprocess.Popen`.

### B. `master_server.py` (The Commander)
*   **Update `input_thread_target` (CLI):**
    *   Parse the new syntax: `exec <slot_id> <task_name> [arg1] [arg2] ...`
        *   *Example:* `exec 0 crack 5e884... a m`
    *   Pack arguments into the message payload: `{'task_name': 'crack', 'args': ['5e884...', 'a', 'm']}`.

## 4. Execution Steps

1.  **Create:** Write `cracker_task.py`.
2.  **Modify:** Update `agent.py` and `master_server.py`.
3.  **Test (Local):**
    *   Generate a hash for "abcde".
    *   Run Master and 1 Agent.
    *   Command: `exec 0 crack <hash> a z`.
    *   Verify the Agent finds it and the Master displays "FOUND: abcde".
