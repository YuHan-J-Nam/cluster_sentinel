#!/usr/bin/env python
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation

#import os
#print(os.environ['OMP_NUM_THREADS'])

import numba
#print("number of threads=", numba.get_num_threads())

from tqdm import tqdm

nstep = 100
n = 1000
infProb = 0.1

@numba.njit(parallel=True)
def update(x, infProb):
    #xNext = np.array(x)
    xNext = np.copy(x)
    #xNext = np.zeros(x.shape)
    n, m = x.shape
    for i in numba.prange(1,n-1):
        for j in numba.prange(1,m-1):
            #xNext[i,j] = x[i,j] \
            #           + (np.random.uniform(0,1) < infProb*x[i-1,j]) \
            #           + (np.random.uniform(0,1) < infProb*x[i+1,j]) \
            #           + (np.random.uniform(0,1) < infProb*x[i,j-1]) \
            #           + (np.random.uniform(0,1) < infProb*x[i,j+1])
            #xNext[i,j] += (np.random.uniform(0,1) < infProb/1.414*x[i-1,j-1])
            #xNext[i,j] += (np.random.uniform(0,1) < infProb/1.414*x[i+1,j-1])
            #xNext[i,j] += (np.random.uniform(0,1) < infProb/1.414*x[i-1,j+1])
            #xNext[i,j] += (np.random.uniform(0,1) < infProb/1.414*x[i+1,j+1])

            xNext[i-1,j] += x[i,j]/5*infProb
            xNext[i+1,j] += x[i,j]/5*infProb
            xNext[i,j-1] += x[i,j]/5*infProb
            xNext[i,j+1] += x[i,j]/5*infProb
            xNext[i,j] -= x[i,j]*4/5*infProb

    #return (xNext > 0)
    return xNext

from scipy import signal
def updateWithConv2D(x):
    #m = np.array([[1/1.414, 1, 1/1.414],
    #              [1, 0, 1],
    #              [1/1.414, 1, 1/1.414]])
    m = np.array([[0, 1, 0],
                  [1, 1, 1],
                  [0, 1, 0]], dtype=x.dtype)
    m /= m.sum()
    return signal.convolve2d(x, m, boundary='fill', mode='same')

snapshots = np.zeros((nstep,n,n))
x = np.zeros((n,n))

ii = np.random.randint(1,n-1)
jj = np.random.randint(1,n-1)
x[ii,jj] = 1000
snapshots[0] = x

for istep in tqdm(range(1, nstep)):
    #snapshots[istep] = #update(snapshots[istep-1], infProb)
    snapshots[istep] = updateWithConv2D(snapshots[istep-1])

fig = plt.figure()
    
im = plt.imshow(snapshots[0], cmap='gray');
def update(i):
    im.set_array(snapshots[i])
    return im

ani = animation.FuncAnimation(fig, update, frames=len(snapshots), interval=100)

plt.show()

#ani.save('ani.gif', writer='imagemagick', fps=5)
