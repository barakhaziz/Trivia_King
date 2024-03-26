import socket
import threading
import struct
import random
import time

# Constants
UDP_PORT = 13117
TCP_PORT = 5555
MAGIC_COOKIE = 0xabcddcba
GAME_DURATION = 10  # in seconds

class TriviaServer:
    def __init__(self):
        self.server_name = "AwesomeTriviaServer"
        self.clients = []

    def start(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind(('0.0.0.0', UDP_PORT))
        print("Server started, listening on IP address 172.1.0.4...")
        threading.Thread(target=self.broadcast_message).start()

    def broadcast_message(self):
        while True:
            # Broadcast the message to all devices on the network
            broadcast_address = ('<broadcast>', UDP_PORT)
            message = struct.pack("!Ib32sH", MAGIC_COOKIE, 0x2, self.server_name.encode('utf-8'), TCP_PORT)
            self.udp_socket.sendto(message, broadcast_address)
            # Sleep for a short duration to avoid flooding the network
            time.sleep(1)  # You can adjust the sleep duration as needed




