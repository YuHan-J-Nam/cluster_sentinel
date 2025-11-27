#!/usr/bin/env python
from concurrent.futures import ProcessPoolExecutor
#from concurrent.futures import ThreadPoolExecutor
import time
import os
import numpy as np

def fun(index, data):
    print(f"Sub fuction is executed PID={os.getpid()}")
    time.sleep(5)
    return data**2

import random
def doCircArea(index, r, nDim, nTotal):
    random.seed(index)
    aSqr = (2*r)**nDim
    nAccept = 0

    for i in range(nTotal):
        rNewSq = 0
        for d in range(nDim):
            xi = random.uniform(-r, r)
            rNewSq += xi**2
        rNew = rNewSq**0.5
        if rNew < r:
            nAccept += 1

    print(index, aSqr, nAccept, nTotal)
    time.sleep(10-index)
    return aSqr, nAccept, nTotal

def makeBigData(index, size):
    data = np.ones(size)
    return data

print(f"Main process is started PID={os.getpid()}")
#fun()
#myData = np.random.uniform(0, 1, size=(30, 100,100))

executor = ProcessPoolExecutor(max_workers=3)
#executor = ThreadPoolExecutor(max_workers=3)
jobs = []
#for i in range(myData.shape[0]):
for i in range(10):
    print(f"Submitted subproc{i}")
    #executor.submit(fun, i, myData[i])
    #executor.submit(fun, i)
    #job = executor.submit(doCircArea, i, 1, 2, 10000)
    job = executor.submit(makeBigData, i, 1000000000)
    jobs.append(job)
print("Finished submitting subprocesses")

#aSqr, nAccept, nTotal = 0, 0, 0
for index, job in enumerate(jobs):
    print(f"Retrieving result of {index}")
    _ = job.result()
    #Q_aSqr, _nAccept, _nTotal = job.result()
    print(f"..... got the result")
    #aSqr = _aSqr
    #nAccept += _nAccept
    #nTotal += _nTotal
#print(aSqr, nAccept, nTotal, (aSqr*nAccept/nTotal))

#print(executor)
#print(dir(executor))
#help(executor.submit)

