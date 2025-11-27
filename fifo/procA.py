#!/usr/bin/env python
import os
import time
import tempfile
import numpy as np
import pickle

# tempdir = tempfile.mkdtemp()
# tempfilePath = f'{tempdir}/shared.fifo'
tempfilePath = 'shared.fifo'
print(f"FIFO filename = {tempfilePath}")

# fout = open("shared.dat", "w")
os.mkfifo(tempfilePath)  # Instead of storing output in hard drive, create temporary RAM file

fout = open(tempfilePath, "wb")
datas = []
for i in range (10):
	data = np.random.uniform(0, 1, 15)

	print("writing data to fifo ", i)
	# fout.write(f'data produced by process A {i}\n')
	# fout.write(data)
	datas.append(data)

# Serialize our data (using pickle)
pickle.dump(datas, fout)

#fout.flush()  # Force data save into file
#time.sleep(1)
fout.close()
os.remove('shared.fifo')
