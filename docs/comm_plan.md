# Communication & Task Execution Implementation Plan

## Objective
Implement bi-directional communication between the Master Server and Agents to enable:
1.  **Task Execution:** Master sends a command to run a specific Python script (task) on the client.
2.  **Result Retrieval:** Client sends back the computed results (stdout) to the Master.
3.  **Control:** Master can stop a running task ("STOP") or terminate the agent completely ("END").
4.  **Verification:** Execute dummy tasks to verify the pipeline.

## 1. Protocol Design

We will extend the current `pickle`-based communication to support structured messages.

### Data Structures

**Base Message Format (Dict):**
```python
{
    "type": "str",  # Message type
    "payload": "any" # The actual data
}
```

### Message Types

**1. Agent -> Master**
*   `HEARTBEAT`: Standard CPU/RAM stats.
    *   Payload: `{'cpu': float, 'ram': float}`
*   `TASK_RESULT`: Output or result from a task.
    *   Payload: `{'task_id': str, 'status': 'COMPLETED'|'RUNNING'|'ERROR', 'data': str}`

**2. Master -> Agent**
*   `EXECUTE`: Start a task.
    *   Payload: `{'task_id': str, 'script': 'script_name.py', 'args': []}`
*   `STOP_TASK`: Stop the currently running task.
    *   Payload: `{'task_id': str}`
*   `END`: Terminate the agent process.
    *   Payload: `None`

## 2. Agent Implementation (`agent.py`)

The agent needs to move from a simple `while True: send; sleep` loop to an event-driven loop using `select` to handle incoming commands without blocking heartbeats.

### Key Components
1.  **`TaskManager` Class:**
    *   Manages `subprocess.Popen` instances.
    *   Methods: `start_task(script)`, `stop_task()`, `check_status()`.
    *   Captures `stdout` and `stderr`.

2.  **Main Loop Refactoring:**
    *   Use `select.select([sock], [], [], timeout=INTERVAL)`
    *   **On Read (`sock`):** Receive command -> Dispatch to `TaskManager` or handle `END`.
    *   **On Timeout (Heartbeat):** Collect system stats -> Send `HEARTBEAT`.
    *   **Task Polling:** In every loop iteration, check `TaskManager` for new output or completion -> Send `TASK_RESULT`.

## 3. Master Implementation (`master_server.py`)

The Master needs a way to inject commands into the `handle_client` threads.

### Key Components
1.  **Command Injection (CLI):**
    *   A background thread in `master_server.py` that reads `stdin` (user input).
    *   Parses commands like: `exec <client_id> <script>`, `stop <client_id>`, `end <client_id>`.
    *   Puts commands into a global `command_queues` dictionary: `{client_id: queue.Queue()}`.

2.  **`handle_client` Refactoring:**
    *   Currently blocks on `conn.recv()`.
    *   Switch to `select.select([conn], [], [], timeout=0.5)`.
    *   **On Read (`conn`):** Process `HEARTBEAT` (update shared mem) or `TASK_RESULT` (print/log).
    *   **On Timeout/Loop:** Check the client's specific `Queue`. If a command exists, pickle and send it to the agent.

## 4. Implementation Steps

### Step 1: Update Protocol & Agent
*   Modify `agent.py` to send wrapped messages `{'type': 'HEARTBEAT', 'payload': ...}`.
*   Implement the `select` loop in `agent.py`.
*   Implement `TaskManager` to run `dummy_task.py`.

### Step 2: Update Master Logic
*   Modify `handle_client` to unwrap messages and handle `HEARTBEAT` (keeping existing shared memory logic).
*   Add the `input_thread` for CLI commands.
*   Implement the command queue system to pass CLI commands to the specific client thread.

### Step 3: Verification
1.  Start Master.
2.  Start Agent.
3.  Verify Dashboard still updates (Heartbeats working).
4.  Type `exec 0 dummy_task.py` in Master console.
5.  Verify Agent starts process and Master receives "Working..." (or completion).
6.  Type `stop 0` and verify Agent kills process.
7.  Type `end 0` and verify Agent quits.
