import os
import socket
import threading
import struct
import sys

UDP_PORT = 13117
MAGIC_COOKIE = 0xabcddcba

class TriviaClient:
    def __init__(self, name):
        self.name = name
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind(('0.0.0.0', UDP_PORT))
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = True

    def start(self):
        print(f"Client {self.name} started, listening for offer requests...")
        self.listen_to_broadcast()

    def listen_to_broadcast(self):
        while True:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                magic_cookie, msg_type = struct.unpack("!Ib", data[:5])
                if magic_cookie == MAGIC_COOKIE and msg_type == 0x2:
                    server_name = data[5:37].decode('utf-8').strip()
                    server_port = struct.unpack("!H", data[37:39])[0]
                    print(f"Received offer from {server_name} at address {addr[0]}, connecting...")
                    self.connect_to_server((addr[0], server_port))
                    break
            except Exception as e:
                print(f"Error while listening for offers: {e}")

    def connect_to_server(self, server_addr):
        try:
            self.tcp_socket.connect(server_addr)
            self.tcp_socket.sendall(f"{self.name}\n".encode('utf-8'))
            threading.Thread(target=self.receive_server_data).start()

        except Exception as e:
            print(f"Error connecting to server: {e}")
            sys.exit(1)

    def receive_server_data(self):
        while self.running:
            try:
                data = self.tcp_socket.recv(1024).decode('utf-8')
                if data:
                    #print(data)  # Print the received message
                    self.send_user_input()
            except Exception as e:
                print(f"Error receiving data from server: {e}")
                break


    def send_user_input(self):
        while self.running:
            try:
                user_input = input()
                self.tcp_socket.sendall(user_input.encode('utf-8') + b'\n')
            except KeyboardInterrupt:
                print("Exiting...")
                self.running = False
                self.tcp_socket.close()
                os._exit(0)





