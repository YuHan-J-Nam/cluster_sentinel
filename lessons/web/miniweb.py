#!/usr/bin/env python
import socket

# Host "0.0.0.0" means allow all connections
# No two ports should be the same
HOST, PORT = "0.0.0.0", 9876

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen()

# Check status
print(f"Mini web server is starting on port={PORT}")

# Receive data
conn, addr = s.accept()
data = conn.recv(1024).decode()
print(f"Data received: {data}")

# Send response
content = "Custom content"
resp = f"HTTP/1.1 200 OK\r\nContent-Length:{len(content)}\r\n\r\n{content}"
conn.sendall(resp.encode())

conn.close()
s.close()
