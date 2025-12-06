# Asyncio Implementation Plan for Cluster Sentinel

## Objective
Refactor the Master Server (`master_server.py`) to use Python's `asyncio` library instead of `threading` + `select.select()`. This will create a more efficient, event-driven architecture for handling multiple client connections and the command CLI concurrently.

## Why Asyncio?
The current implementation uses a "polling" loop with `select.select(timeout=0.1)` to check for both network data and internal command queues. While functional, this:
1.  Wastes CPU cycles waking up 10 times a second per client even when idle.
2.  Introduces latency (up to 100ms) for commands.
3.  Requires manual timeout management.

`asyncio` allows us to simply `await` events (socket data OR queue items) and wake up exactly when something happens.

## Key Architectural Changes

### 1. Replace `threading.Thread` with `asyncio.Task`
*   **Current:** `handle_client` is a function run in a `threading.Thread`.
*   **New:** `handle_client` will be an `async def` coroutine run as an asyncio Task.
*   The standard `socket` library will be replaced with `asyncio.StreamReader` and `asyncio.StreamWriter`.

### 2. Replace `queue.Queue` with `asyncio.Queue`
*   Thread-safe queues block threads. Asyncio queues are designed to be `await`-ed without blocking the event loop.
*   We will need to pass the loop or use `asyncio.run_coroutine_threadsafe` if we still have threads (like the CLI), or move the CLI to be async as well.

### 3. Handling the CLI (Blocking Input)
*   Standard input (`sys.stdin`) is blocking. We cannot easily `await` it in a cross-platform way without external libraries (`aioconsole`).
*   **Strategy:** Keep the CLI in a separate **Thread**, but have it communicate with the Async Event Loop using `loop.call_soon_threadsafe` or by putting items into a queue that the async loop watches.

### 4. Shared Memory & Multiprocessing
*   The `Collector` and `Dashboard` are separate **Processes** (`multiprocessing`). This remains unchanged.
*   `asyncio` will run **inside** the `collector_process_target`.

## Implementation Details

### `master_server.py` Refactor

1.  **`collector_process_target`**:
    *   Instead of standard socket setup, use `await asyncio.start_server(...)`.
    *   Entry point: `asyncio.run(main_collector_loop(...))`.

2.  **`handle_client` (Async Coroutine)**:
    *   Signature: `async def handle_client(reader, writer, shm, lock, cmd_queue):`
    *   **The "Select" Replacement:** Use `asyncio.wait` or `asyncio.gather` to wait for TWO things simultaneously:
        *   `reader.read()` (Data from Agent)
        *   `cmd_queue.get()` (Command from CLI)
    *   *Challenge:* `reader.read()` is not easily cancelable if we are waiting on the queue.
    *   *Better Approach:* Two background tasks per client? Or a loop that `await`s a `Future`?
    *   *Preferred Pattern:* Run a `consumer_task` for the Queue and a `producer_task` for the Socket.
        *   `client_reader_task`: Loops `await reader.read()`, processes Heartbeats/Results.
        *   `client_writer_task`: Loops `await cmd_queue.get()`, writes to socket.
        *   If `reader` closes (EOF), cancel the writer task and cleanup.

3.  **Timeout Logic**:
    *   Wrap the `reader.read()` call in `asyncio.wait_for(..., timeout=10.0)`.
    *   If it times out, close the connection.

### 3. Migration Steps

1.  **Phase 1: Async Skeleton**
    *   Create `async_master_server.py` (or modify existing) to set up `asyncio.start_server`.
    *   Verify it accepts connections.

2.  **Phase 2: Client Handler**
    *   Implement the reader loop (Heartbeats).
    *   Verify data updates Shared Memory (Lock usage must be careful—locks are thread-blocking, not async-blocking, but since we use `multiprocessing.Lock`, it might block the loop. Ideally, we minimize lock holding time).

3.  **Phase 3: Command Queue**
    *   Implement the writer loop (Commands).
    *   Bridge the CLI thread to the Async Queue.

## Risks & Mitigations

*   **Multiprocessing Lock:** `multiprocessing.Lock` is a blocking OS semaphore. If we acquire it in the Async Loop and it blocks, the *entire* server pauses.
    *   *Mitigation:* Keep critical sections extremely short (just the `shm` write). The OS context switch is fast enough that this is usually acceptable for a simple server.
*   **CLI Integration:** Getting blocking `stdin` to talk to `asyncio` can be tricky.
    *   *Mitigation:* Use a `threading.Thread` for the CLI that calls `loop.call_soon_threadsafe(queue.put_nowait, item)`.

## Success Criteria
*   Server handles multiple clients.
*   Dashboard updates.
*   CLI commands work (`exec`, `stop`, `end`).
*   **Idle timeout works** automatically via `asyncio.wait_for`.
*   CPU usage is near zero when idle.
