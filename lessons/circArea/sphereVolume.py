#!/usr/bin/env python
# The above is a shebang (instructs which program to use)

# Import libraries
import random
import numpy as np

# Define variables
r = 1
volumeCube = (2*r)**3
nAccept = 0
nTotal = 100000 # The larger the number of trials, the more accurate the area becomes

for i in range(nTotal):
	# Choose random x,y,z coordinate in cube
	x = random.uniform(-r, r)
	y = random.uniform(-r, r)
	z = random.uniform(-r, r)

	# Calculate hypotenuse
	rNew = np.sqrt(x**2 + y**2 + z**2)
	# Check if length of hypotenuse is less than r
	if rNew < r:
		nAccept += 1

volume = volumeCube * nAccept/nTotal
print(volume)
