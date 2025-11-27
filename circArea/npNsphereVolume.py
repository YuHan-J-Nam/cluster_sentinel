#!/usr/bin/env python
# The above is a shebang (instructs which program to use)

# Import libraries
import random
import numpy as np

def npCalcVol():
	# Define variables
	r = 1
	nDim = 3
	volumeNDim = (2*r)**nDim
	nAccept = 0
	nTotal = 100000 # The larger the number of trials, the more accurate the area becomes

	# Set up array of random coordinates in nDim
	xi = np.random.uniform(-r, r, (nTotal, nDim))

	rNewSq = np.sum(xi**2, axis=1)

	# If we want to do it using only numpy
	# rNew = np.sqrt(np.random.uniform(-r, r, (nTotal, nDim))**2).sum(axis=1))

	# Check if length of hypotenuse is less than r
	# nAccept = (rNew < r).sum() # For faster speed we can compare rNewSq with r**2
	nAccept = (rNewSq < r**2).sum()

	return volumeNDim, nAccept, nTotal

print(*npCalcVol())
