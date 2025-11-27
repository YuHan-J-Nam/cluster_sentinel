from numba import njit, prange
import numpy as np, time, numba

@njit(parallel=True)
def work(n):
    s = 0
    for i in prange(n):
        s += i % 7
    return s

t0 = time.time()
work(10**10)
print("Elapsed:", time.time()-t0, "Threads:", numba.get_num_threads())

