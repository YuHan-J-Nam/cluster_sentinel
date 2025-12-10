# Cluster Deployment Guide: Testing with Dummy Task

This guide outlines the steps to run the "Cluster Sentinel" with the Master Server on your local machine and Agents on the HPC cluster (compute nodes), connected via an SSH tunnel and a custom bridge.

## Prerequisites
*   **Local Machine:** Python 3 installed.
*   **Cluster:** Access via SSH.
*   **Network:** You must be able to SSH into the login node.

---

## Step 1: Start the Master Server (Local Machine)

Open a terminal on your **local machine**.

1.  Navigate to the project directory.
2.  Start the Master Server. It will listen on `127.0.0.1` (localhost) because it expects traffic to come through the SSH tunnel.

```bash
python master_server.py --host 127.0.0.1 --port 13579
```
*   *Output:* You should see `[Collector] Listening on 127.0.0.1:13579`.
*   *Keep this terminal open.* This is your command center.

---

## Step 2: Establish SSH Tunnel (Local Machine)

Open a **second terminal** on your **local machine**.

1.  Create a "Reverse Tunnel". This maps port `13579` on the cluster's login node (localhost side) back to port `13579` on your laptop.

```bash
# Replace 'user' and 'login_node_ip' with your credentials
ssh -R 13579:localhost:13579 user@login_node_ip
```
*   *Status:* You are now logged into the cluster. The tunnel is active in the background of this session.

---

## Step 3: Start the Port Forwarding Bridge (Cluster Login Node)

In the **same terminal** from Step 2 (where you are SSH'd into the cluster):

1.  The compute nodes cannot talk to `localhost` on the login node. They need to talk to the login node's **Public/LAN IP**.
2.  We use `port_forward.py` to bridge the gap between the Public IP and the Tunnel.

```bash
# First, find your login node's IP address (look for eth0 or similar)
ip addr show 
# Let's assume the IP is 10.0.0.5 or similar.

# Run the bridge. 
# --host 0.0.0.0: Bind to ALL interfaces so compute nodes can reach it.
# --local-port 13580: The port compute nodes will connect to.
# --remote-port 13579: The port of the SSH tunnel (localhost).
python port_forward.py --host 0.0.0.0 --local-port 13580 --remote-port 13579
```
*   *Output:* `[Bridge] Listening on 0.0.0.0:13580...`

---

## Step 4: Submit Agents (Cluster Login Node)

Open a **third terminal** on your **local machine**, and SSH into the cluster normally (no tunnel needed this time, or use a multiplexer like `tmux` on the server).

1.  Navigate to the project directory on the cluster.
2.  Edit the Slurm script `utils/run_10_agents.slurm` to point to the Bridge.

```bash
nano utils/run_10_agents.slurm
```
*   **Change `MASTER_HOST`** to the **Login Node's IP** (the one you found in Step 3, e.g., `10.0.0.5`).
*   **Change `MASTER_PORT`** to `13580` (the Bridge port).

3.  Submit the job.
```bash
sbatch utils/run_10_agents.slurm
```
*   *Output:* `Submitted batch job <JOB_ID>`

---

## Step 5: Verification & Execution (Local Machine)

Return to your **Master Server terminal** (Terminal 1).

1.  **Watch Connections:** You should see 10 agents connecting:
    ```text
    [Collector] Connected by ('127.0.0.1', 54321)
    [Collector] Reserving slot 0 for ...
    ...
    ```
    *(Note: They will all look like they come from 127.0.0.1 because they are flowing through the tunnel).*

2.  **Check Dashboard:** Open `http://localhost:8080`. You should see 10 CPU/RAM bars.

3.  **Run Dummy Task:** In the Master CLI, execute the dummy task on Slot 0.
    ```text
    exec 0 dummy
    ```
    *   *Expected Output:*
        ```text
        Queued EXECUTE 'dummy' for slot 0...
        [Client 0] Status: STARTED
        [Client 0][Task ...][stdout] Dummy task started...
        [Client 0][Task ...][stdout] Working... (1/5)
        ...
        [Client 0][Task ...][stdout] Task complete.
        ```

4.  **Shutdown:**
    *   Stop agents: `scancel <JOB_ID>` (on cluster).
    *   Stop Master: `Ctrl+C` (on local).
