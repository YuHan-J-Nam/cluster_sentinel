#!/usr/bin/env python
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation

from tqdm import tqdm

nstep = 1000
n = 100
infProb = 0.1

snapshots = np.zeros((nstep,n,n))
x = np.zeros((n,n))

ii = np.random.randint(n)
jj = np.random.randint(n)
x[ii,jj] = 1
snapshots[0] = x

for istep in tqdm(range(1, nstep)):
    xNext = np.array(x)
    for i in range(n):
        for j in range(n):
            if i != 0:
                xNext[i,j] += (np.random.uniform(0,1) < infProb*x[i-1,j])
            if i+1 != n:
                xNext[i,j] += (np.random.uniform(0,1) < infProb*x[i+1,j])
            if j != 0:
                xNext[i,j] += (np.random.uniform(0,1) < infProb*x[i,j-1])
            if j+1 != n:
                xNext[i,j] += (np.random.uniform(0,1) < infProb*x[i,j+1])
    x = (xNext > 0)

    snapshots[istep] = x

fig = plt.figure()
    
im = plt.imshow(snapshots[i], cmap='gray');
def update(i):
    im.set_array(snapshots[i])
    return im

ani = animation.FuncAnimation(fig, update, frames=len(snapshots), interval=20)

plt.show()

ani.save('ani.gif', writer='imagemagick', fps=10)
