#!/usr/bin/env python
import socket
import struct
import os
import sys
sys.path.append("./circArea")
from higherDimension import doCalculation

HOST, PORT = "0.0.0.0", 14230

print(f"[Client] Client is connecting to server")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT)) # Connect to initiated server
print(f"[Client] Connection is established")

# Receive data
cmd = s.recv(1024) # Size of data from server
print(f"[Client] Received from server: {cmd}")  # For debugging
try:
	while True:
		if cmd == b"WHO":
			# Send pid
			pid = os.getpid()
			data = struct.pack('i', pid)
			s.sendall(data)
		elif cmd == b"COMPUTE":
			print(f"[Client] Running computation")

			volumeNDim, nAccept, nTotal = doCalculation()
			data = struct.pack('f 2i', volumeNDim, nAccept, nTotal)
			s.sendall(data)
		elif cmd == b"END":
			raise "Finishing..."
except:
	s.close()
