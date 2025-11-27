#!/usr/bin/env python
# The above is a shebang (instructs which program to use)

# Import libraries
import random
import numpy as np
import numba

### Process is slow because Python is an interpreted language -> so use numba
@numba.jit
def doCalculation():
	# Define variables
	r = 1
	nDim = 3
	volumeNDim = (2*r)**nDim
	nAccept = 0
	nTotal = 10000000 # The larger the number of trials, the more accurate the area becomes

	for i in range(nTotal):
		rNewSqrd = 0
		# Choose random coordinate in cube
		for d in range(nDim):
			xi = np.random.uniform(-r, r)
			rNewSqrd += xi**2

		# Calculate hypotenuse
		rNew = np.sqrt(rNewSqrd)

		# Check if length of hypotenuse is less than r
		if rNew < r:
			nAccept += 1

	return volumeNDim, nAccept, nTotal

volumeNDim, nAccept, nTotal = doCalculation()
volume = volumeNDim * nAccept/nTotal
print(volume)
