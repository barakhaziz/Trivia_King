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
        self.running = True
        self.server_name = "AwesomeTriviaServer"
        self.clients = []

        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(('0.0.0.0',TCP_PORT))
        self.tcp_socket.listen(5)  # Listen for incoming connections

    def start(self):
        # define UDP socket
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind(('0.0.0.0', UDP_PORT))
        print(f"Server started, listening on IP address {self.udp_socket.getsockname()[0]}...")
        threading.Thread(target=self.broadcast_message).start()
        threading.Thread(target=self.wait_for_clients).start()

    def broadcast_message(self):
        while True:
            # UDP Broadcast the message to all devices on the network
            broadcast_address = ('<broadcast>', UDP_PORT)
            message = struct.pack("!Ib32sH", MAGIC_COOKIE, 0x2, self.server_name.encode('utf-8'), TCP_PORT)
            self.udp_socket.sendto(message, broadcast_address)
            # Sleep for a short duration to avoid flooding the network
            time.sleep(1)  # You can adjust the sleep duration as needed

    def wait_for_clients(self):
        start_time = time.time()
        self.udp_socket.settimeout(GAME_DURATION)
        self.tcp_socket.settimeout(1)
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                conn, _ = self.tcp_socket.accept()  # Accept TCP connection
                threading.Thread(target=self.handle_tcp_client, args=(conn, addr)).start()
            except socket.timeout:
                if time.time() - start_time >= GAME_DURATION:
                    self.running = False
                    print("great!")
                    #self.start_game()
                    break

    def handle_tcp_client(self, conn, addr):
        team_name = conn.recv(1024).decode('utf-8').strip()
        self.clients.append((team_name, addr))
        print(f"Team {team_name} connected from {addr}")
        conn.close()







