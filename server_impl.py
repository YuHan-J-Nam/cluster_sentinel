#!/usr/bin/env python
import socket
import struct # for encoding/decoding

HOST, PORT = "0.0.0.0", 14230

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))  # Allocate resources
s.listen()  # Start server

print(f"[Server] Server is starting on port={PORT}")

conn, addr = s.accept()
print(f"[Server] Connection is established with {addr}")

try:
	while True:
		# Send data
#		conn.sendall(b'WHO')
		conn.sendall(b'COMPUTE') # b for encrypting into bytes

		# Receive data
		data = conn.recv(1024) # 1024 bytes of data (32-bit)
		volumeNDim, nAccept, nTotal = struct.unpack('f 2i', data)  # Can use arguments to define other types of data i, s, etc.
		print(f"[Server] Received data: {volumeNDim}, {nAccept}, {nTotal}")
except Exception as e:
	print(e)
finally:  # When job is terminated
	conn.close()
	s.close()
