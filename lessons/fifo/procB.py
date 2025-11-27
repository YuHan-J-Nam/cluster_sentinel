#!/usr/bin/env python
import os
import sys
import time
import pickle

fifoName = sys.argv[1]

fin = open(fifoName, "rb")
data = pickle.load(fin)

#for _ in range(100):
#	data = fin.read()
#	print(data)
#	time.sleep(1)
print(data)
print(len(data))
print(type(data))
print(type(data[0]), len(data[0]), data[0].shape())
fin.close()
