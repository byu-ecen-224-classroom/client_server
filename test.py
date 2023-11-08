import socket
import time

HOST = "localhost"  # The remote host
PORT = 2240  # The same port as used by the server
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))

    with open("photos/123456789/2023-11-03T16:52:29.378815-06:00.bmp", "rb") as f:
        s.sendall(b"123456789")
        file_data = f.read()
        s.sendall(file_data[:50])
        # time.sleep(10)
        # s.sendall(file_data[50:])

    data = s.recv(1024)
    print(f"Received {data}")
