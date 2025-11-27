#!/usr/bin/env python
# The above is a shebang (instructs which program to use)

# Import libraries
import random
import numpy as np

# Define variables
r = 1
areaSqr = 4*r*r
nAccept = 0
nTotal = 1000 # The larger the number of trials, the more accurate the area becomes

for i in range(nTotal):
	# Choose random x,y coordinate in square
	x = random.uniform(-r, r)
	y = random.uniform(-r, r)

	# Calculate hypotenuse
	rNew = np.sqrt(x**2 + y**2)
	# Check if length of hypotenuse is less than r
	if rNew < r:
		nAccept += 1

area = areaSqr * nAccept/nTotal
print(area)
