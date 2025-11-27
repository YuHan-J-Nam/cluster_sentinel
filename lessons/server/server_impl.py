#!/usr/bin/env python
import socket
import struct # for encoding/decoding
from concurrent.futures import ThreadPoolExecutor
import threading

lock = threading.Lock()

aSqr = 0.
nAcceptAll, nTotalAll = 0, 0

def handle_client(conn, addr):
	global aSqr, nAcceptAll, nTotalAll
	try:
		while True:
			if nTotalAll > 100000000:
				conn.sendall(b'END')
				conn.close()
				break

			# Send data
#			conn.sendall(b'WHO')
			conn.sendall(b'COMPUTE') # b for encrypting into bytes

			# Receive data
			data = conn.recv(1024) # 1024 bytes of data (32-bit)
			volumeNDim, nAccept, nTotal = struct.unpack('f 2i', data)  # Can use arguments to define other types of data i, s, etc.
			print(f"[Server: Thread] Received data from {addr}: {volumeNDim}, {nAccept}, {nTotal}")
			with lock:
				nAcceptAll += nAccept
				nTotalAll += nTotal

	except Exception as e:
		print(e)
	finally:  # When job is terminate
		conn.close()

if __name__ == "__main__":

	HOST, PORT = "0.0.0.0", 14230

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.bind((HOST, PORT))  # Allocate resources
	s.listen()  # Start server

	print(f"[Server] Server is starting on port={PORT}")

	cons = []
	for i in range(2):
		conn, addr = s.accept()
		print(f"[Server] Connection is established with {addr}")
		cons.append((conn, addr))

#	for conn, addr in cons:
#		handle_client(conn, addr)

	with ThreadPoolExecutor(max_workers=2) as executor:
		for conn, addr in cons:
			executor.submit(handle_client, conn, addr)
	s.close()
