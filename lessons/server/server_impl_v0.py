#!/usr/bin/env python
import socket
import struct # for encoding/decoding
from concurrent.futures import ThreadPoolExecutor

HOST, PORT = "0.0.0.0", 14230

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))  # Allocate resources
s.listen()  # Start server

print(f"[Server] Server is starting on port={PORT}")

aSqr = 0.
nAcceptAll, nTotalAll = 0, 0

cons = []
for i in range(2):
	conn, addr = s.accept()
	print(f"[Server] Connection is established with {addr}")
	cons.append((conn, addr))

try:
	while True:
		# Need something to break out of while loop
		if nConn <= 0:  # Temporary method
			break
		for i, (conn, addr) in enumerate(cons):
			if nTotalAll > 10000000:
				conn.sendall(b'END')
				conn.close()
				nConn -= 1
				cons[i] = (None, addr)
				break

			# Send data
#			conn.sendall(b'WHO')
			conn.sendall(b'COMPUTE') # b for encrypting into bytes

			# Receive data
			data = conn.recv(1024) # 1024 bytes of data (32-bit)
			volumeNDim, nAccept, nTotal = struct.unpack('f 2i', data)  # Can use arguments to define other types of data i, s, etc.
			print(f"[Server] Received data: {volumeNDim}, {nAccept}, {nTotal}")
			nAcceptAll += nAccept
			nTotalAll += nTotal
except Exception as e:
	print(e)
finally:  # When job is terminated
	for conn, addr in cons:
		if conn != None:
			conn.close()
	s.close()
