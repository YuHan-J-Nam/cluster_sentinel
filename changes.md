# Code Changes Explanation: Remote Task Execution

## Overview
We transformed the system from a **passive monitoring tool** (one-way data flow) into an **active command-and-control system** (bi-directional).

Previously, the Agent simply shouted its stats at the Master every 2 seconds. Now, the Master can tell the Agent to run Python scripts (`subprocess`), and the Agent streams the output back to the Master in real-time.

## 1. The Protocol Upgrade
**Old Way:** The Agent pickled a dictionary `{cpu, ram}` and sent it. The Master expected exactly that.
**New Way:** We wrapped everything in a standardized message format using a "Header" (type) and "Body" (payload).

```python
{
    "type": "HEARTBEAT",   # or "EXECUTE", "TASK_RESULT", "STOP_TASK"
    "payload": { ... }     # The actual data (stats, script name, output lines)
}
```
**Why?** This allows the receiver to know *how* to treat the incoming data. A heartbeat updates the dashboard; a task result gets printed to the console.

## 2. The Agent Refactor (`agent.py`)

### The Problem with `time.sleep()`
The old agent had a loop: `Send Stats -> Sleep 2s -> Repeat`.
If the Master sent a "STOP" command while the agent was sleeping, the agent wouldn't hear it for 2 seconds. Even worse, if we ran a task that took 10 seconds, the Agent would stop sending heartbeats, and the Master would think it died.

### The Solution: `select.select()`
We replaced `time.sleep` with `select.select`. This is a standard System Call (syscall) available in OS kernels. It tells the OS: *"Wake me up if ANY of these file descriptors have data to read, OR if 1 second passes."*

We monitor three things simultaneously:
1.  **The Network Socket:** "Did the Master send a command?"
2.  **The Task's STDOUT/STDERR:** "Did the running script print something?"
3.  **The Timeout:** "Has it been 2 seconds? If so, send a heartbeat."

### The `TaskManager` Class
We wrapped `subprocess.Popen` in a class.

#### What is `subprocess.Popen`?
`subprocess.Popen` is the Python tool for spawning new processes (programs). Unlike simpler commands like `os.system("python task.py")` which just run a command and wait for it to finish, `Popen` gives us **fine-grained control** over the new process while it is running.

*   **Why `Popen`?** We need the agent to stay alive *while* the task is running. `os.system` would block the entire agent until the task finished. `Popen` starts the task in the background and gives us a handle (object) to control it.
*   **Pipes (`stdout=subprocess.PIPE`):** We connect "pipes" to the standard output and error streams of the new process. This acts like a hose: as the task prints text, it flows through the pipe into our Python script. This allows us to read the task's output line-by-line in real-time and forward it to the Master, rather than waiting for the whole task to finish to see what happened.

*   **Non-blocking I/O:** We set the task's output pipes to "non-blocking." This ensures that if we try to read a line and it's not there, the Agent doesn't freeze. It just moves on to the next iteration of the loop.

## 3. The Master Refactor (`master_server.py`)

### Threading & The Producer-Consumer Pattern
The Master now does two things at once:
1.  **Listens to the User (CLI):** A new thread `input_thread_target` waits for you to type commands (e.g., `exec 0 script.py`).
2.  **Listens to Agents:** The `handle_client` threads maintain connections with agents.

**The Challenge:** How do we get a command typed in Thread A to be sent out by Thread B?

**The Solution: Queues (`queue.Queue`)**
We implemented a thread-safe Queue for each connected client.
1.  **Producer (CLI Thread):** When you type `exec 0 ...`, the CLI thread puts that command into Client 0's Queue.
2.  **Consumer (Client Thread):** The thread handling Client 0 checks its Queue constantly. If it finds a command, it pickles it and sends it over the socket.

## Summary of Data Flow

1.  **User** types `exec 0 task.py`.
2.  **CLI Thread** puts command in `client_queues[0]`.
3.  **Client Handler Thread** sees the command, sends `{"type": "EXECUTE", ...}` to Agent.
4.  **Agent** receives message, `TaskManager` spawns `subprocess`.
5.  **Subprocess** prints "Working...".
6.  **Agent** reads "Working...", sends `{"type": "TASK_RESULT", ...}` to Master.
7.  **Master** receives result, prints to console.
