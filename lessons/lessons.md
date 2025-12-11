# Lessons Learned

This document summarizes the key programming concepts and techniques explored in the `lessons/` directory.

## 1. Monte Carlo Simulations & Numerical Methods
**Files:** `circArea/`, `stockprice.py`

*   **Monte Carlo Method:** estimating values (like area or volume) using random sampling.
    *   Calculated the area of a circle and volume of N-dimensional spheres by checking the ratio of points falling inside the shape vs. the bounding box.
    *   Observed that accuracy increases with the number of trials ($N$).
*   **Optimization:**
    *   **NumPy:** Using vectorized operations (e.g., `np.sum`, `np.random.uniform`) is significantly faster than standard Python loops.
    *   **Numba:** Using `@numba.jit` to compile Python functions to machine code for high-performance numerical loops.
*   **Dimensionality:** Explored how volume calculations scale with higher dimensions.

## 2. Simulation & Visualization
**Files:** `diffusion/`

*   **Grid-based Simulation:** modeled 2D diffusion where particles (or values) spread to neighbors based on probability.
*   **Visualization:** Used `matplotlib.pyplot` (`imshow`) and `matplotlib.animation` to create real-time animations and save them as GIFs.
*   **Optimization Techniques:**
    *   **Parallelism:** Used `@numba.njit(parallel=True)` with `prange` to parallelize grid updates.
    *   **Convolution:** Replaced manual neighbor-checking loops with 2D convolution (`scipy.signal.convolve2d`) for cleaner and faster code.

## 3. Parallelism & Concurrency
**Files:** `procExecutor/`

*   **Process vs. Thread:**
    *   **ProcessPoolExecutor:** Used for CPU-bound tasks (e.g., heavy calculations). Each process has its own memory space.
    *   **ThreadPoolExecutor:** Used for I/O-bound tasks. Threads share the same memory space.
*   **Futures:** Used `executor.submit()` to schedule tasks asynchronously and retrieved results using `job.result()`.
*   **System Calls:** Explored `os.system` and `os.popen` to execute shell commands directly from Python.

## 4. Inter-Process Communication (IPC)
**Files:** `fifo/`, `sharedMem/`

*   **Named Pipes (FIFO):**
    *   Used `os.mkfifo` to create a special file acting as a pipe.
    *   One process writes to the pipe, and another reads from it, allowing data exchange between separate processes.
    *   Used `pickle` to serialize complex Python objects (like lists or arrays) for transmission through the pipe.
*   **Shared Memory:**
    *   Used `multiprocessing.shared_memory.SharedMemory` to allocate a block of RAM accessible by multiple processes.
    *   **Zero-Copy:** Mapped NumPy arrays directly to the shared memory buffer (`buffer=shm.buf`), allowing processes to read/write the same data array without copying.
    *   **Synchronization:** Used `multiprocessing.Lock` to prevent race conditions when multiple processes write to the shared array simultaneously.

## 5. Networking
**Files:** `server/`, `web/`

*   **Socket Programming:**
    *   Created TCP servers and clients using `socket.socket`.
    *   **Server:** Binds to a host/port, listens for connections, and accepts clients.
    *   **Client:** Connects to the server's address.
*   **Binary Protocols:**
    *   Used `struct.pack` and `struct.unpack` to send precise binary data (floats, integers) over the network, ensuring efficiency and strict typing compared to plain text.
*   **Concurrency:** Implemented a threaded server (`ThreadPoolExecutor`) to handle multiple client connections simultaneously.
*   **HTTP:** Built a minimal web server (`miniweb.py`) that parses raw HTTP requests and sends standard HTTP responses (`HTTP/1.1 200 OK`).

## 6. Financial Modeling (In Progress)
**Files:** `stockprice.py`

*   **Random Walk:** Simulated stock price movements using cumulative sums of random steps.
*   **Time Series Analysis:** Implemented moving averages to smooth data trends.
*   **Algorithmic Trading:** Started implementing a basic logic to buy/sell based on the crossover of price and moving average.