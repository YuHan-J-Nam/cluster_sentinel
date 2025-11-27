#!/usr/bin/env python
import numpy as np
import time
from multiprocessing import shared_memory, Process, Lock

def myFunction(index, shm_name, shape, dtype):
#	print(f"Subprocess {index} is running...")
	shm = shared_memory.SharedMemory(name=shm_name)
	arr = np.ndarray(shape, dtype=dtype, buffer=shm.buf)

	# Actual subprocess
	for i in range(len(arr)):
#		lock.acquire()
		with lock:
			arr[i] += 1
#			lock.release()
		time.sleep(0.001)

#	print(f'Subprocess {index}: array = {arr}')
#	time.sleep(1)
#	print(f'..........{index} done')

	return index**2

if __name__ == '__main__':
	# To avoid clashes while r/w between subprocesses, use Lock()
	lock = Lock()

	arr = np.ndarray(1000, dtype='float')
	# Need to set a unique name for shm so that multiple users can create their own saved memory (shm is placed in /dev/shm)
	# Or just set no name and let name auto-generate
	shm = shared_memory.SharedMemory(create=True, size=arr.nbytes)
	print(f"Shared memory dev name: {shm.name}")
	arr = np.ndarray(arr.shape, dtype=arr.dtype, buffer=shm.buf)
#	print(f"Created shared memory: {arr}")

	procs=[]
	for i in range(100):
		proc = Process(target=myFunction, args=(i, shm.name, arr.shape, arr.dtype))
		procs.append(proc)

	for proc in procs:
		proc.start()
	print("Finished submitting jobs")

	for proc in procs:
		proc.join()

#	print(proc1, dir(proc1))

	print(f"Result is...")
	print(f'Main Process: array = {arr[:10]}')
#	print(result1, result2)
	print(f"After finishing... = {arr.sum()}")

	shm.close()
	shm.unlink()
