# Implementation Plan: Bi-Directional Communication & Command Execution

## 1. Current State Analysis
**Confirmed:** The current architecture is strictly **Uni-Directional**.
*   **Agent:** Connects -> Loops -> Sends Data -> Sleeps. (No code to receive data).
*   **Master:** Accepts -> Loops -> Receives Data. (No code to send data).

## 2. Proposed Architecture: Bi-Directional "Command & Control"
To enable the Master Server to send commands (like "SHUTDOWN" or "EXECUTE_TASK") to the Agent, we need to upgrade the communication pipeline.

### 2.1. The "Command Queue" Pattern (Master Side)
The Master Server needs a way to inject commands into the specific thread handling an agent.
*   **Mechanism:** We will use `multiprocessing.Queue` (or `queue.Queue` since threads are used for clients).
*   **Flow:**
    1.  **Admin Interface:** The Main Process (or a new input thread) reads commands from the CLI (e.g., `shutdown client_1`).
    2.  **Dispatch:** The Main Process puts this command into a global dictionary of queues: `client_queues[client_id].put("SHUTDOWN")`.
    3.  **Collector Thread:** Inside `handle_client`, the loop changes. It now checks:
        *   *Is there data from the socket?* (Read & Process Stats)
        *   *Is there a command in my Queue?* (Get & Send to Agent)

### 2.2. Non-Blocking Agent Loop (Client Side)
The Agent can no longer just `sleep(2)`. It needs to be listening constantly while still sending stats on time.
*   **Mechanism:** `select` module.
*   **Flow:**
    *   Loop:
        *   Use `select.select([socket], [], [], timeout=0.1)` to check for incoming messages.
        *   **If Message Received:** Parse it. Is it "SHUTDOWN"? Is it "EXECUTE"? Run logic.
        *   **If Time to Send:** Check `time.time()`. If 2 seconds have passed, collect stats and send.

### 2.3. Protocol Definition
We need to distinguish between "Stats" and "Commands". We will wrap messages in a simple structure.

**Message Structure (Pickled Dict):**
*   **Agent -> Master (Stats):**
    ```python
    {
        "type": "STATS",
        "payload": {"cpu": 10.5, "ram": 40.0}
    }
    ```
*   **Master -> Agent (Command):**
    ```python
    {
        "type": "COMMAND",
        "cmd": "SHUTDOWN",  # or "EXECUTE"
        "args": []          # e.g., ["script_name.py"]
    }
    ```
*   **Agent -> Master (Response):**
    ```python
    {
        "type": "RESPONSE",
        "status": "OK",     # or "ERROR"
        "output": "..."
    }
    ```

## 3. Implementation Steps

### Phase 1: Master Server "Command Center"
1.  **Global Registry:** Create a `manager = multiprocessing.Manager()` and a shared `client_queues` dictionary to map `client_id` -> `Queue`.
2.  **Input Thread:** Create a new thread `admin_console()` that runs in the Master Server.
    *   It listens for user input (stdin).
    *   Parses: `kill <ip>` or `run <ip> <task>`.
    *   Puts the command object into the correct queue.
3.  **Update `handle_client`:**
    *   Register itself in `client_queues` upon connection.
    *   Use `select` (or non-blocking checks) to read from socket.
    *   Check `queue.get_nowait()` to see if there are commands to send.
    *   Send commands using `socket.sendall(pickle.dumps(cmd_dict))`.

### Phase 2: Agent "Listener" Logic
1.  **Refactor Main Loop:** Remove the simple `sleep(2)`.
2.  **Implement `select` Loop:**
    ```python
    inputs = [sock]
    last_send_time = time.time()
    
    while True:
        # Check for incoming data (timeout 0.1s so we don't block)
        readable, _, _ = select.select(inputs, [], [], 0.1)
        
        for s in readable:
            data = s.recv(4096)
            if data:
                process_command(pickle.loads(data))
            else:
                # Server disconnected
                return

        # Check if it's time to send stats
        if time.time() - last_send_time > 2.0:
            send_stats()
            last_send_time = time.time()
    ```

### Phase 3: Task Execution Logic (The "Tasks" Module)
To satisfy "Run certain tasks", we will implement a safe dispatcher in `agent.py`.

1.  **Define `tasks.py` (or internal function):**
    ```python
    def run_task(task_name):
        if task_name == "clean_logs":
            return subprocess.check_output(["rm", "-rf", "/tmp/logs"])
        elif task_name == "check_disk":
            return subprocess.check_output(["df", "-h"])
        else:
            return "Unknown Task"
    ```
2.  **Handle "EXECUTE" Command:**
    *   Agent receives: `{"type": "COMMAND", "cmd": "EXECUTE", "args": ["check_disk"]}`
    *   Agent calls `run_task("check_disk")`.
    *   Agent sends back: `{"type": "RESPONSE", "output": "Filesystem..."}`.

### Phase 4: Shutdown Logic
1.  **Handle "SHUTDOWN" Command:**
    *   Agent receives `SHUTDOWN`.
    *   Sets a flag `running = False`.
    *   Breaks the loop and exits cleanly.

## 4. Security & Safety Note
*   **Pickle Warning:** We are still using `pickle`. In a production environment, this is unsafe (RCE vulnerability). For this prototype, it is acceptable, but **JSON** is preferred if we have time.
*   **Command Whitelisting:** The "Run Task" feature **MUST** use a whitelist (like the `if/elif` block above). **NEVER** allow the master to send arbitrary shell strings (e.g., `os.system(cmd_from_server)`), as this is a massive security hole.

## 5. Summary of Changes
*   **`master_server.py`:** Add `admin_console` thread, `client_queues`, and bi-directional logic in `handle_client`.
*   **`agent.py`:** Refactor loop with `select`, add `process_command` handler, and task execution logic.
