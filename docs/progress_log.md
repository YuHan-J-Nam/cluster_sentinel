# Progress Log: The Cluster Sentinel Development

This document details the step-by-step development of "The Cluster Sentinel", a distributed server monitoring system. It maps the implementation of `agent.py` and `master_server.py` to the project plan and documents the specific technical skills and learnings applied at each stage.

## Phase 1: The Agent (Data Collection & Transmission)

**Script:** `agent.py`
**Goal:** Create a client-side script to harvest system stats and send them to a central server.

### Step 1.1: Data Harvesting
- **Implementation:** Created the `get_system_stats()` function.
- **Technique:** Utilized the `psutil` library (standard Python ecosystem) to fetch real-time metrics.
    - `psutil.cpu_percent(interval=1)` blocks for 1 second to calculate CPU usage.
    - `psutil.virtual_memory().percent` grabs current RAM usage.

### Step 1.2: The Socket Client
- **Implementation:** The `main()` function establishes the network connection.
- **Learnings Applied:**
    - **Socket Programming (Learning 1.1):** Used `socket.socket(socket.AF_INET, socket.SOCK_STREAM)` to create a TCP socket. This is the fundamental building block for network communication, as explored in `client_impl.py`.
    - **Data Serialization (Learning 4.4):** Used `pickle` to convert the Python dictionary returned by `get_system_stats()` into a byte stream suitable for network transmission. This mirrors the technique used in the FIFO examples (`fifo/procA.py`).
- **Challenges & Solutions:**
    - **Robustness:** Added a `try...except` block for `ConnectionRefusedError` to prevent the agent from crashing if the server isn't running. It retries every 5 seconds, ensuring the agent is resilient.

## Phase 2: The Collector (Server Backend & IPC)

**Script:** `master_server.py` (Collector logic)
**Goal:** Create a server that receives data from multiple agents and stores it efficiently for another process to read.

### Step 2.1: The Socket Listener
- **Implementation:** Defined `collector_process_target` and `handle_client`.
- **Learnings Applied:**
    - **Socket Server (Learning 1.1):** The collector binds to a host/port and uses `s.listen()` to accept incoming connections.
    - **Multithreading (Optimization):** Unlike the basic single-threaded server in `server_impl.py`, I used `threading.Thread` to handle each client connection (`handle_client`). This allows the collector to manage multiple agents simultaneously without blocking.

### Step 2.2: Shared Memory Setup
- **Implementation:** Integrated `multiprocessing.shared_memory`.
- **Learnings Applied:**
    - **Shared Memory (Learning 2.2):** Used `shared_memory.SharedMemory` to create a block of RAM accessible by both the Collector and Dashboard processes. This avoids the overhead of writing to disk or using a database for such volatile, high-frequency data.
    - **Struct Packing:** Used the `struct` module to define a rigid binary format (`'iff'` -> int, float, float) for storing `client_id`, `cpu`, and `ram`. This makes reading/writing to the raw memory buffer precise and efficient.

### Step 2.3: Writing with Locks
- **Implementation:** Inside `handle_client`, data is written to `shm.buf`.
- **Learnings Applied:**
    - **Synchronization (Learning 2.2):** Utilized `multiprocessing.Lock` to protect write operations. This ensures that the Dashboard doesn't try to read the memory block at the exact nanosecond the Collector is updating it, which could lead to corrupted data.
- **Challenge - Multi-Client Management:**
    - **Problem:** How to store data for multiple unknown clients in a single block of memory?
    - **Solution:** Implemented a "Slot System". `find_slot` searches for an empty chunk of memory (where `client_id` is 0). The client is assigned that index. When they disconnect, the slot is cleared (zeroed out), making it available for a new agent.

## Phase 3: The Dashboard (Web Server Interface)

**Script:** `master_server.py` (Dashboard logic)
**Goal:** Visualize the data stored in shared memory without interfering with the collector.

### Step 3.1: The Mini Web Server
- **Implementation:** Defined `dashboard_process_target`.
- **Learnings Applied:**
    - **HTTP Protocol (Learning 1.2):** Manually constructed HTTP headers (`HTTP/1.1 200 OK...`) and content. This low-level approach (similar to `web/miniweb.py`) provides a deep understanding of how web servers actually function under the hood.

### Step 3.2: Dynamic HTML Generation
- **Implementation:** Reading from `shm` and formatting strings.
- **Learnings Applied:**
    - **Reading Shared Memory:** The dashboard attaches to the same `shm_name`. It loops through the slots, unpacks the binary data using `struct.unpack`, and checks if a client is active (`client_id != 0`).
    - **HTML/CSS:** Injected the unpacked values into an HTML template. Added CSS for a "hacker-style" terminal look and used a `<meta refresh>` tag to auto-reload the page, creating a "live" monitoring effect without complex JavaScript.

## Phase 4: Integration & Orchestration

**Script:** `master_server.py` (Main block)
**Goal:** Run the Collector and Dashboard as concurrent processes.

### Step 4.1: Process Manager
- **Implementation:** The `if __name__ == "__main__":` block.
- **Learnings Applied:**
    - **Multiprocessing (Learning 3.1):** Used `multiprocessing.Process` to spawn two independent processes: one for the Collector and one for the Dashboard. They run in parallel, utilizing multiple CPU cores.
    - **Resource Management:** A critical part of this phase was handling the lifecycle of Shared Memory.
- **Challenge - Memory Leaks:**
    - **Problem:** If the script crashed, the shared memory segment would remain in the OS, causing `FileExistsError` on the next run or resource warnings.
    - **Solution:** Implemented a robust cleanup strategy.
        1.  **Startup:** Try to unlink any existing stale memory block before creating a new one.
        2.  **Shutdown:** Used a `try...finally` block to ensure `shm.close()` and `shm.unlink()` are called when the user hits `Ctrl+C`.

## Phase 5: HPC Deployment & Network Engineering

**Goal:** Deploy the "Cluster Sentinel" on a real high-performance computing (HPC) cluster (Slurm) and enable communication between isolated compute nodes and a master server running on a local laptop.

### Step 5.1: Environment Diagnosis
- **Challenge:** Compute nodes failed to connect to the master server when running via `sbatch`.
- **Action:** Created a diagnostic script `net_debug.slurm` to inspect the compute node's network environment (`ip addr`, `ip route`, `ping`).
- **Finding:** Compute nodes are on a private network but can route traffic to the Login Node's public IP. They cannot access the user's local machine directly.

### Step 5.2: Code Refactoring for Flexibility
- **Action:** Refactored `agent.py` and `master_server.py` to replace hardcoded IPs with command-line arguments using `argparse`.
- **Learning (CLI Usability):** Hardcoding values impedes deployment testing. Using `argparse` allows dynamic configuration (e.g., `python agent.py --host 1.2.3.4 --port 9999`) without changing source code, essential for testing different network paths quickly.

### Step 5.4: The "Tunnel Bridge" Solution
- **Problem:** The user wanted the Master Server on their laptop.
    - `ssh -R` creates a reverse tunnel, but it typically binds only to `127.0.0.1` on the Login Node.
    - Compute Nodes cannot talk to the Login Node's `127.0.0.1`.
    - The user lacked root access to install tools like `socat` or change `GatewayPorts` in sshd config to expose the tunnel publicly.
- **Solution:** Developed `port_forward.py`, a custom Python TCP bridge.
    - **Logic:** It listens on `0.0.0.0` (Public Interface) on a specific port (e.g., 13580) and manually forwards every byte to `127.0.0.1` (The SSH Tunnel).
- **Learning (Network Socket Forwarding):** Built a bi-directional data pump using Python's `socket` and `threading` modules. This effectively implemented a user-space NAT/Port-Forwarder, demonstrating that application-layer code can solve infrastructure-layer restrictions.

**Final Architecture:**
`Compute Node` -> `[TCP Connection]` -> `Login Node (Bridge Script)` -> `[Localhost Connection]` -> `SSH Tunnel Endpoint` -> `[Encrypted SSH Tunnel]` -> `Local Laptop` -> `Master Server`.

## Phase 6: Reliability Engineering

**Goal:** Ensure the system handles unexpected failures gracefully, specifically when agents are forcibly killed.

### Step 6.1: Handling "Dirty" Disconnects
- **Problem:** When a compute node job was cancelled (`scancel`), the `agent.py` process was killed instantly. It could not send a TCP FIN packet to close the connection.
    - **Symptom:** The Master Server kept the connection open (waiting for data), and the Dashboard continued to display the last known stats for the dead client indefinitely.
- **Solution:** Implemented a **Heartbeat Timeout** in `master_server.py`.
    - Added `conn.settimeout(5.0)` to the client handling loop.
    - If no data is received for 5 seconds (implying the agent is dead or stuck), the server raises a `socket.timeout` exception.
- **Result:** The exception handler catches the timeout, breaks the loop, and triggers the `finally` block. This block clears the client's slot in Shared Memory (`client_id = 0`), causing the Dashboard to automatically remove the dead entry on its next refresh.

## Phase 7: Testing & Deployment Utilities

**Goal:** Create independent testing utilities to verify Slurm job submission and network bridging without relying on the full Agent/Master complexity.

### Step 7.1: The Dummy Task
- **Implementation:** Created `utils/dummy_task.py` and `utils/run_dummy_task.slurm`.
- **Purpose:** A minimal script that simulates work (logging time and sleeping) to verify that `sbatch` jobs are running correctly on compute nodes and generating output, independent of network connectivity.

### Step 7.2: Enhanced Port Bridge
- **Implementation:** Updated `port_forward.py` to include a `--host` argument.
- **Reasoning:** Previously hardcoded to `0.0.0.0`, explicitly allowing the bind address to be configured provides greater flexibility for testing on different network interfaces (e.g., binding only to a specific VPN IP or localhost for secure testing).


