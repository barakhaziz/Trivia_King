import socket
import threading
import struct
import sys
import os
import random

# Constants
UDP_PORT = 13117
MAGIC_COOKIE = 0xabcddcba
SERVER_ADDRESS = ('<server_ip>', UDP_PORT)  # Replace <server_ip> with the actual server IP


class TriviaClient:
    def __init__(self,name):
        self.name=name

    def start(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind(('0.0.0.0', UDP_PORT))  # Bind to any available port
        print(f"Client- {self.name} started, listening for offer requests...")
        self.listen_to_broadcast()


    def listen_to_broadcast(self):
        while True:
            data, addr = self.udp_socket.recvfrom(1024)
            magic_cookie, msg_type = struct.unpack("!Ib", data[:5])
            if magic_cookie == MAGIC_COOKIE and msg_type == 0x2:
                server_name = data[5:37].decode('utf-8').strip()
                server_port = struct.unpack("!H", data[37:39])[0]
                print(f"Received offer from {server_name} at address {addr[0]}, connecting...")
                #self.connect_to_server((addr[0], server_port))
                break
