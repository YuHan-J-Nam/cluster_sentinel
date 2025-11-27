#!/usr/bin/env python
import numpy as np
import time
from multiprocessing import shared_memory, Process, Lock
import os

if __name__ == '__main__':
	arr = np.ndarray(10, dtype='float')
	shm = shared_memory.SharedMemory(name='shm_yhnam')
	arr = np.ndarray(arr.shape, dtype=arr.dtype, buffer=shm.buf)

	for i in range(len(arr)):
		arr[i] = len(arr)-i

# Unsuccessful: Programs in different shells cannot access the same shared memory
