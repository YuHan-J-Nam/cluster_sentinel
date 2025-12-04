# Project Plan: The Cluster Sentinel

*A Lightweight Distributed Server Monitor*

## Project Overview

**Goal:** Build a monitoring system where "Agent" processes on different machines send system health data (CPU, RAM) to a central "Master" server. The Master server displays this data on a real-time web dashboard.

**Core Concepts Covered:** Socket Programming, Multiprocessing, Shared Memory (IPC), Locks, HTTP Protocol, Serialization (Pickle), System Commands.

## Phase 1: The Agent (Data Collection & Transmission)

**Focus:** System Interaction & Basic Networking

In this phase, you will build the client-side script that runs on the machine you want to monitor. It needs to gather data and send it out.

### Step 1.1: Data Harvesting
Create `agent.py`.

Write a function `get_system_stats()` that returns a dictionary (e.g., {'cpu': 15.5, 'ram': 40.2}).

### Step 1.2: The Socket Client

Implement a socket client in `agent.py` (refer to `server/client_impl.py`).

The agent should connect to localhost (or your server IP) on a specific port (e.g., 5000).

Use `pickle` to serialize the stats dictionary.

Send the pickled data over the socket.

Add a `time.sleep(2)` loop so it sends data every 2 seconds.

✅ **Checkpoint 1**

- [x] Run a dummy server (simple script that just prints what it receives).
- [x] Run `agent.py`.
- [x] Verify: Does the dummy server print a dictionary containing real-time CPU/RAM stats every 2 seconds?

## Phase 2: The Collector (Server Backend & IPC)

**Focus:** Socket Server, Shared Memory, & Synchronization

This is the hardest part. The server needs to listen to the agent and write that data to a place where the web dashboard can see it later.

### Step 2.1: The Socket Listener

Create `master_server.py`.

Setup a socket server that listens for connections (refer to `server/server_impl.py`).

When a client connects, receive the data, unpickle it, and print it to the console.

### Step 2.2: Shared Memory Setup

**The Problem:** The "Socket Listener" gets the data, but the "Web Server" (Phase 3) needs to read it. They will be separate processes.

**The Solution:** Use `multiprocessing.shared_memory` (refer to `sharedMem/shm1.py`).

Create a structured array or a shared memory block large enough to hold stats for a few nodes (e.g., store Client ID, CPU %, RAM %).

### Step 2.3: Writing with Locks

Modify the Socket Listener to write the received agent data into the Shared Memory block.

**Critical:** Use `multiprocessing.Lock` (refer to `sharedMem/sharedMem.py`) to ensure you don't write to memory at the exact same moment the web server tries to read it.

✅ **Checkpoint 2**

- [x] Run `agent.py`.
- [x] Run `master_server.py`.
- [x] Create a temporary script `test_reader.py` that attaches to the shared memory and prints the values.
- [x] Verify: When `agent.py` updates, does `test_reader.py` show the new numbers?

**Notes:**
- Encountered and fixed a `UserWarning: resource_tracker: There appear to be 1 leaked shared_memory objects` error. The issue was in `master_server.py`, where the shared memory segment was not being unlinked correctly on termination, especially if the script was linking to a segment from a previous crashed run. The fix involved adding a flag (`shm_created`) to ensure `shm.unlink()` is only called by the process that originally created the segment.

## Phase 3: The Dashboard (Web Server Interface)

**Focus:** HTTP Protocol & Reading Shared Memory

Now you need a way to see the data without looking at the console. You will build a read-only web server.

### Step 3.1: The Mini Web Server

Create `dashboard.py` (or add a function to `master_server.py`).

Implement a basic HTTP server using sockets (refer to `web/miniweb.py`).

It should listen on a different port (e.g., 8080).

It should accept a browser request and return a valid HTTP string (HTTP/1.1 200 OK...).

### Step 3.2: Dynamic HTML Generation

Inside the request handler, attach to the Shared Memory block created in Phase 2.

Read the current CPU/RAM stats (remember to use the Lock!).

Generate an HTML string that includes these numbers.

Bonus: Use a simple HTML `<meta http-equiv="refresh" content="2">` tag to make the page reload automatically every 2 seconds.

✅ **Checkpoint 3**

- [x] Start the Agent and the Collector.
- [x] Start the Dashboard server.
- [x] Open a web browser to `http://localhost:8080`.
- [x] Verify: Do you see the CPU stats? Does the page refresh with new numbers?

## Phase 4: Integration & Orchestration

**Focus:** Multiprocessing & System Management

Finally, combine the Collector and the Dashboard into a single manageable application.

### Step 4.1: The Process Manager

Refactor `master_server.py` to be the main entry point.

Use `multiprocessing.Process` to launch:

- The Collector (Socket Listener) function.
- The Dashboard (Web Server) function.

Pass the SharedMemory name and the Lock object to both processes so they can share access.

### Step 4.2: The "Sentinel" Alert Logic (Optional but Recommended)

In the Collector process, add a simple check:

`if cpu_usage > 90:`

Execute a system command (using `os.popen`) to sound a beep, send a desktop notification, or simply print "CRITICAL WARNING" to the server logs.

### Step 4.3: Deployment (Slurm Test)

If you have access, deploy the Agent on the school server (using slurm or just running it in the background) and keep the Master on your laptop.

Ensure the school server can reach your laptop's IP (requires being on the same network/VPN).

✅ **Final Checkpoint**

- [x] Run `python master_server.py`.
- [x] Run `python agent.py`.
- [x] Open Browser.
- [x] Stress test your computer (open many apps).
- [x] Verify: Does the graph/number on the website go up? If >90%, does the alert trigger?

**Notes:**
- Refactored `master_server.py` to handle multiple (up to 10) agents by expanding the shared memory and assigning each client a slot.
- Switched from `multiprocessing.Process` to `threading.Thread` for handling client connections in the collector, significantly improving efficiency.
- The dashboard now displays all connected clients.

## Troubleshooting HPC Deployment

### Initial Testing Observations:

1.  **Login Node -> Login Node (127.0.0.1):** Master on login, Agent on login. Result: **Worked**.
    *   *Analysis:* Both components on the same machine, using localhost. Expected behavior.
2.  **Login Node -> Local Machine (127.0.0.1 with implicit tunnel):** Master on local machine, Agent on login node (connecting to 127.0.0.1). Result: **Worked**.
    *   *Analysis:* This likely implies an active SSH reverse tunnel from the login node to the local machine, allowing `127.0.0.1` on the login node to refer to the local machine's service.
3.  **salloc (Compute Node) -> Local Machine (127.0.0.1 with implicit tunnel):** Master on local machine, Agent on compute node via `salloc` (connecting to 127.0.0.1). Result: **Worked**.
    *   *Analysis:* Similar to #2, suggests the `salloc` environment (or the user's interactive session while controlling it) also benefits from the SSH tunnel, or `salloc` was used to run an interactive session on the Login Node, not a Compute Node. If it was on a Compute Node, it implies that particular Compute Node also has an active tunnel bound to its local `127.0.0.1` interface which reaches the local machine.
4.  **salloc (Compute Node) -> Local Machine (Login Node's Public IP: 163.180.2.245):** Master on local machine, Agent on compute node via `salloc`. Result: **Did not work**.
    *   *Analysis:* Compute nodes typically cannot reach public IPs (like the login node's external IP) due to network isolation/firewalls.
5.  **sbatch (Compute Node) -> Local Machine (127.0.0.1):** Master on local machine, Agent on compute node via `sbatch`. Result: **Did not work**.
    *   *Analysis:* `sbatch` jobs run in a non-interactive, detached environment on a compute node. The `127.0.0.1` address on the compute node refers to itself, not the local machine. Any SSH tunnels active in the user's interactive session are not present in the batch job environment.
6.  **sbatch (Compute Node) -> Local Machine (Login Node's Public IP: 163.180.2.245):** Master on local machine, Agent on compute node via `sbatch`. Result: **Did not work**.
    *   *Analysis:* Combination of #4 and #5. Compute nodes are isolated from public IPs, and `sbatch` jobs lack interactive session context.

### Problem Diagnosis:
The failures in scenarios involving `sbatch` and direct connection to public IPs from compute nodes highlight two main issues:
1.  **Network Isolation:** Compute nodes on HPC clusters are usually behind firewalls and on private networks, preventing direct access to external IPs or even the login node's public IP.
2.  **`127.0.0.1` Scope:** `127.0.0.1` (localhost) is always specific to the machine it's run on. An `sbatch` job on a compute node sees its own `127.0.0.1`, not the user's local machine or the login node.
3.  **SSH Tunnel Dependence:** The successful "local machine" tests likely rely on an active SSH reverse tunnel, which is typically tied to an interactive SSH session and not automatically available to `sbatch` jobs.

### Plan Moving Forward:

To resolve these connectivity issues and enable `agent.py` to reliably communicate with `master_server.py` from `sbatch` jobs, we will proceed with the following steps:

1.  **Refactor Code for Flexibility:**
    *   **Status:** *Completed*. `agent.py` and `master_server.py` have been modified to accept master host and port via command-line arguments using `argparse`. This eliminates the need to hardcode IPs and allows for easier testing across different network configurations.
2.  **Diagnose Compute Node Network Environment:**
    *   **Action:** User to run the provided `net_debug.slurm` script on the HPC cluster using `sbatch`.
    *   **Goal:** Obtain detailed network information (IP addresses, hostname, routing table) from the perspective of a compute node. This will help identify the internal IP address of the login node or any other reachable internal network resources.
3.  **Propose Connection Strategies based on Diagnostics:**
    *   **Option A (Recommended): Run Master on Login Node:** If the login node's internal IP is discoverable and reachable from compute nodes, the most straightforward solution is to run `master_server.py` on the login node (listening on `0.0.0.0`) and point `agent.py` (from `sbatch` jobs) to that internal IP.
    *   **Option B (Advanced): Master on Local Machine with Advanced Tunneling:** If the master *must* remain on the local machine, it will require maintaining a robust SSH reverse tunnel from the login node to the local machine, *and* configuring the login node to allow compute nodes to access this tunnel (e.g., using `GatewayPorts` in `sshd_config` or a `socat` relay on the login node). This is generally more complex to set up and maintain.

### Phase 2 Testing (Refinement & Verification):

Following the initial analysis, further tests were conducted to pinpoint the exact connectivity capabilities of the compute nodes:

7.  **Master on Login Node (0.0.0.0) -> Agent on Compute Node (Targeting Login Public IP):** Result: **Worked**.
    *   *Analysis:* Compute nodes *can* route traffic to the Login Node's public IP. The Login Node receives this traffic successfully.
8.  **Master on Login Node (0.0.0.0) -> Agent on Compute Node (Targeting Internal Gateway 192.168.1.1):** Result: **Did not work**.
    *   *Analysis:* The internal IP structure was not as predicted, or the service wasn't bound correctly to that specific internal interface. However, since test #7 worked, this path is unnecessary.
9.  **Master on Local Machine (127.0.0.1) -> SSH Tunnel -> Agent on Compute Node (Targeting Login Public IP):** Result: **Did not work**.
    *   *Analysis:* This confirmed that the standard `ssh -R` tunnel binds only to `127.0.0.1` on the Login Node. Traffic arriving at the Login Node's Public IP from the Compute Node could not cross over to the localhost-bound tunnel listener.

### Final Solutions:

Based on the testing, two robust configurations were established for running the "Cluster Sentinel".

#### Solution A: Master on Login Node (Easiest)
This configuration runs the collector directly on the cluster's head node.
*   **Master:** Run `python master_server.py --host 0.0.0.0 --port 13579` on the Login Node.
*   **Agent:** Submit `sbatch` jobs where `agent.py` connects to the Login Node's **Public IP** (`163.180.2.245`).
*   **Dashboard:** Access via SSH Tunnel (`ssh -L 8080:localhost:8080 user@login_node`) and open `localhost:8080` on your laptop.

#### Solution B: Master on Local Machine (Advanced "Bridge")
This configuration keeps the Master and Dashboard on your local machine, allowing you to monitor the cluster without running persistent services on the login node. It overcomes the lack of `socat` and root permissions on the server using a custom Python bridge.

**The Architecture:**
`Agent (Compute Node)` -> `Login Node Public IP:13580` -> `port_forward.py (Bridge)` -> `Login Node Localhost:13579` -> `SSH Reverse Tunnel` -> `Local Laptop:13579` -> `Master Server`

**Steps to Deploy:**
1.  **Local Laptop:** Start the Master Server.
    ```bash
    python master_server.py --host 127.0.0.1 --port 13579
    ```
2.  **Local Laptop:** Establish the SSH Reverse Tunnel.
    ```bash
    ssh -R 13579:localhost:13579 user@login_node_ip
    ```
3.  **Login Node:** Run the Python Bridge Script (to forward external traffic to the tunnel).
    ```bash
    python port_forward.py --local-port 13580 --remote-port 13579
    ```
4.  **Compute Node:** Submit the Agent job targeting the Bridge port.
    ```bash
    # In sbatch script
    python agent.py --host <LOGIN_NODE_PUBLIC_IP> --port 13580
    ```

**Status:** ✅ **Deployment Troubleshooting Resolved.** Both local and remote master configurations are now fully operational.

## Refinement: Reliability and Robustness

### Issue: Stale Data from Killed Agents
**Observation:** When an agent running via Slurm was cancelled using `scancel`, the process was terminated immediately. The TCP connection on the master server remained "Established" because no FIN packet was sent. This caused the Dashboard to continue displaying the dead client's last known stats indefinitely.

**Fix: Socket Timeouts**
**Implementation:** Modified `master_server.py` to enforce a strict 5-second timeout on `conn.recv()`.
*   **Logic:** Since agents are programmed to send data every 2 seconds, a silence of 5 seconds indicates a failure.
*   **Outcome:** When the timeout triggers, the Master Server drops the connection and clears the Shared Memory slot. The Dashboard updates on its next refresh cycle, removing the "ghost" client.

✅ **Final Reliability Checkpoint**
- [x] Start Master (Local or Remote).
- [x] Start Agent (via `sbatch`).
- [x] Verify Agent appears on Dashboard.
- [x] Run `scancel <job_id>` to kill the Agent.
- [x] Verify: Does the Agent disappear from the Dashboard within ~5-7 seconds?

### Refinement: Testing Utilities (Dec 4, 2025)

To isolate deployment issues from application logic, distinct testing tools were added:
*   **`utils/dummy_task.py` & `utils/run_dummy_task.slurm`:** Simple scripts to verify Slurm job execution and output logging without network dependencies.
*   **`port_forward.py` Update:** Added a `--host` argument to the bridge script, allowing the user to specify the bind address (defaulting to `0.0.0.0`) for more flexible network configurations.

### Refinement: Enhanced Client Identification and Display

**Issue:** Initially, client identification on the dashboard was limited to a hashed integer, which did not provide sufficient detail.

**Fix: Full Address and Slot Index Display**
**Implementation:** `master_server.py` was modified to store and display the full client address tuple (IP and Port) along with its assigned slot index in shared memory and on the web dashboard.
*   **Shared Memory Format:** Changed from `iff` (int, float, float) to `i64sff` (1-based slot ID, 64-byte string for address tuple, float CPU, float RAM).
*   **Slot Assignment:** The `slot_index + 1` value is stored in the shared memory to serve as a 1-based client ID, avoiding conflicts with `0` (which signifies an empty slot) and making the ID directly visible on the dashboard.
*   **Dashboard Display:** The dashboard now retrieves and displays the 1-based `slot_id` and the decoded `(IP, Port)` string for each connected client, providing clearer identification.


