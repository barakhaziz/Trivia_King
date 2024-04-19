import os
import socket
import threading
import struct
import sys
import random
import time



UDP_PORT = 13117
MAGIC_COOKIE = 0xabcddcba
SERVER_ADDRESS = '0.0.0.0'  # For listening for broadcasts
SERVER_NO_RESPONSE_TIMEOUT = 45  # Timeout for server to respond to client connection

class TriviaClient:
    def __init__(self, name=None, is_bot=False):
        if is_bot:
            self.name = "BOT_" + self.generate_random_name()
        else:
            self.name = name if name else "Client"

        self.is_bot = is_bot
        self.tcp_socket = None
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind((SERVER_ADDRESS, UDP_PORT))
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = True



    def generate_random_name(self):
        # Generate a random name from a list of names or by a random string
        names = ['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank', 'Grace', 'Hannah', 'Ivan', 'Jack', 'Kevin', 'Liam',
                 'Mia', 'Nora', 'Oliver', 'Penny', 'Quinn', 'Riley', 'Sophia', 'Tom', 'Ursula', 'Violet', 'Will', 'Xander',
                 'Yara', 'Zoe']
        return random.choice(names)

    def start(self):
        print(f"Client {self.name} started, listening for offer requests...")
        threading.Thread(target=self.send_user_input).start()
        self.listen_to_broadcast()

    def listen_to_broadcast(self):
        while True:
            data, addr = self.udp_socket.recvfrom(1024)
            try:
                magic_cookie, msg_type = struct.unpack("!Ib", data[:5])
                if magic_cookie == MAGIC_COOKIE and msg_type == 0x2:
                    server_name = data[5:37].decode('utf-8').strip()
                    server_port = struct.unpack("!H", data[37:39])[0]
                    print(f"Received offer from {server_name} at address {addr[0]}, connecting...")
                    self.connect_to_server((addr[0], server_port))
                    break
            except struct.error:
                print("Received corrupted data")
            except Exception as e:
                print(f"Error while listening for offers: {e}")

    def connect_to_server(self, server_addr):
        if self.tcp_socket is None:  # Check if the socket needs to be reinitialized
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.settimeout(SERVER_NO_RESPONSE_TIMEOUT)  # Set timeout for response
        try:
            self.tcp_socket.connect(server_addr)
            # set timeout for client is doesnt receive any response from the server
            self.tcp_socket.settimeout(SERVER_NO_RESPONSE_TIMEOUT)
            self.tcp_socket.sendall(f"{self.name}\n".encode('utf-8'))
            if self.is_bot:
                self.bot_behavior()
            else:
                threading.Thread(target=self.receive_server_data).start()
        except socket.error as e:
            print(f"Connection failed: {e}")
            self.tcp_socket.close()  # Properly close the socket on failure to connect
            self.tcp_socket = None  # Reset the socket to None after closing
        except Exception as e:
            print(f"Error connecting to server: {e}")
            self.tcp_socket.close()  # Ensure the socket is closed on error
            self.tcp_socket = None  # Reset the socket to None after closing
            sys.exit(1)

    def receive_server_data(self):
        while self.running:
            try:
                data = self.tcp_socket.recv(1024)
                if data:
                    print(data.decode('utf-8'))
                else:
                    print("Server has closed the connection.")
                    self.close_connection()  # Close on server initiated disconnection
                    break
            except socket.timeout:
                # fix this printing
                print("Server response timed out. set in the function 'connect_to_server' -> self.tcp_socket.settimeout(40)")
                self.close_connection()  # Close connection after timeout
                break
            except socket.error as e:
                print(f"Network error: {e}")
                self.close_connection()  # Close connection on network error
                break
            except RuntimeError as e:
                self.close_connection()
                print(f"Connection closed by server: {e}")
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

    def bot_behavior(self):
        """Simulate bot behavior by waiting for a question and then automatically answering."""
        # bug 2 - fixed
        out_of_game = False  # Flag to indicate whether the bot is out of the game
        while self.running and not out_of_game:
            try:
                # Wait for data from the server
                data = self.tcp_socket.recv(1024).decode('utf-8').strip()
                if "You answered incorrectly and are out of the game." in data:
                    print("Received notification of elimination from game.")
                    out_of_game = True  # Set the flag indicating the bot is out of the game
                    continue  # Continue listening to the server without sending answers

                if data:
                    print(data)  # Print the received message
                    # Only generate an answer if not out of the game
                    if not out_of_game:
                        # Simulate thinking time before sending an answer
                        time.sleep(random.uniform(0.5, 2))
                        answer = random.choice(['T', 'F'])  # Randomly choose an answer
                        print(f"Bot {self.name} answering: {answer}")
                        self.tcp_socket.sendall(answer.encode('utf-8') + b'\n')
            except socket.timeout:
                print(
                    "Server response timed out. set in the function 'connect_to_server' -> self.tcp_socket.settimeout(40)")
                self.close_connection()  # Close connection after timeout
                break
            except socket.error as e:
                print(f"Network error: {e}")
                self.close_connection()  # Close connection on network error
                break
            except RuntimeError as e:
                self.close_connection()
                print(f"Connection closed by server: {e}")
                break

    def close_connection(self):
        print("Server disconnected, listening for offer requests...")
        self.running = False
        self.tcp_socket.close()
        self.tcp_socket = None  # Reset the socket
        self.running = True
        self.listen_to_broadcast()  # Restart listening for UDP broadcasts

    # def close_connection(self):
    #     self.running = False
    #     self.tcp_socket.close()
    #     print("Disconnected from server")





