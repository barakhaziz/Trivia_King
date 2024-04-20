import os
import socket
import threading
import struct
import sys
import random
import time
import msvcrt


UDP_PORT = 13117
MAGIC_COOKIE = 0xabcddcba
SERVER_ADDRESS = '0.0.0.0'  # For listening for broadcasts
SERVER_NO_RESPONSE_TIMEOUT = 45  # Timeout for server to respond to client connection


def print_color(text, color):
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "end": "\033[0m",
    }
    print(colors[color] + text + colors["end"])

class TriviaClient:
    def __init__(self, name=None, is_bot=False):
        if is_bot:
            self.name = self.generate_bot_name()
        else:
            self.name = name if name else "Client"

        self.is_bot = is_bot
        self.tcp_socket = None
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind((SERVER_ADDRESS, UDP_PORT))
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.name_suffix = 0
        self.server_port = None
        self.running = True
        self.server_found = False

    def generate_new_name(self):
        """ Generate a new name by incrementing a suffix. """
        self.name_suffix += 1
        self.name = f"{self.name}_{self.name_suffix}"
        print_color(f"New name generated: {self.name}", "yellow")

    def generate_bot_name(self):
        # Generate a random name from a list of names or by a random string
        names = ['LeBron', 'Kobe', 'Michael', 'Shaquille', 'Tim', 'Dirk', 'Stephen', 'Kevin', 'Kyrie', 'James',
        'Anthony', 'Russell', 'Giannis', 'Carmelo', 'Dwight', 'Chris', 'Damian', 'Blake', 'Paul', 'Derrick',
        'Dwyane', 'Manu', 'Tony', 'Pau', 'Karl', 'John', 'Ray', 'Scottie', 'Charles', 'Patrick',
        'Yao', 'Tracy', 'Grant', 'Penny', 'Vince']
        return f"BOT_{random.choice(names)}"

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
                    self.server_port = struct.unpack("!H", data[37:39])[0]
                    print_color(f"Received offer from {server_name} at address {addr[0]}, connecting...", "green")
                    self.connect_to_server((addr[0], self.server_port))
                    break
                time.sleep(1.3)
            except struct.error:
                print_color("Received corrupted data", "red")
            except Exception as e:
                print_color(f"Error while listening for offers: {e}", "red")
            time.sleep(1.3)


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
            print_color(f"Connection failed: {e}", "red")
            self.close_connection()
        except Exception as e:
            print_color(f"Error connecting to server: {e}", "red")
            self.tcp_socket.close()  # Ensure the socket is closed on error
            self.tcp_socket = None  # Reset the socket to None after closing
            sys.exit(1)

    def receive_server_data(self):
        while self.running:
            try:
                data = self.tcp_socket.recv(1024)
                if data:
                    message = data.decode('utf-8')
                    print(data.decode('utf-8'))
                    if "Name is taken, choose a new one." in message:
                        # Name is taken, generate a new one and reconnect
                        self.generate_new_name()
                        self.close_connection()
                    # here we should verify if the name is taken message
                    # then if so, change the self.name to a new name
                    # and again call the function connect_to_server
                else:
                    #print("receive_server_data: Server has closed the connection.")
                    self.close_connection()  # Close on server initiated disconnection
                    break
            except socket.timeout as e:
                # fix this printing
                print_color("Timeout! server not reachable", "red")
                #print("receive_server_data: Server response timed out. set in the function 'connect_to_server' -> self.tcp_socket.settimeout(40)")
                self.close_connection()  # Close connection after timeout
                break
            except socket.error as e:
                #print(f"receive_server_data: Network error: {e}")
                self.close_connection()  # Close connection on network error
                break
            except RuntimeError as e:
                self.close_connection()
                #print(f"receive_server_data: Connection closed by server: {e}")
                break

    # def send_user_input(self):
    #     while self.running:
    #         try:
    #             if msvcrt.kbhit():
    #                 user_input = msvcrt.getche()
    #                 if user_input == b'\r':  # Check if the enter key is pressed
    #                     print()  # Move to the next line
    #                     self.tcp_socket.sendall(
    #                         b'\n')  # Send newline character to server to process the input as completed
    #                 elif user_input == b'\x03':  # Check for Ctrl+C
    #                     raise KeyboardInterrupt
    #                 else:
    #                     self.tcp_socket.sendall(
    #                         user_input + b'\n')  # Send each character immediately followed by a newline
    #         except socket.error as e:
    #             print(f"send_user_input: Network error: {e}")
    #             self.running = False
    #             self.tcp_socket.close()
    #             os._exit(0)
    #         except KeyboardInterrupt:
    #             print("send_user_input: Exiting...")
    #             self.running = False
    #             self.tcp_socket.close()
    #             os._exit(0)
    #         except Exception as e:
    #             print(f"send_user_input: Error sending data: {e}")
    #             self.running = False
    #             self.tcp_socket.close()
    #             os._exit(1)
    #         time.sleep(0.1)

    def send_user_input(self):
        while self.running:
            try:
                user_input = input()
                self.tcp_socket.sendall(user_input.encode('utf-8') + b'\n')
                time.sleep(1.3)
            except socket.error as e:
                #print(f"send_user_input: Network error: {e}")
                self.running = False
                self.tcp_socket.close()
                os._exit(0)
            except KeyboardInterrupt:
                print_color("send_user_input: Exiting...", "red")
                self.running = False
                self.tcp_socket.close()
                os._exit(0)
            except Exception as e:
                #print(f"send_user_input:Error sending data: {e}")
                self.running = False
                self.tcp_socket.close()
                os._exit(1)
            time.sleep(1.3)

    def bot_behavior(self):
        """Simulate bot behavior by waiting for a question and then automatically answering."""
        print_color("Bot behavior started.", "green")
        out_of_game = False  # Flag to indicate whether the bot is out of the game
        while self.running:
            try:
                # Wait for data from the server
                data = self.tcp_socket.recv(1024).decode('utf-8').strip()
                if "You answered incorrectly and are out of the game." in data:
                    print_color("You answered incorrectly and are out of the game.", "magenta")
                    out_of_game = True  # Set the flag indicating the bot is out of the game
                    continue  # Continue listening to the server without sending answers
                if f"Name is taken, choose a new one." in data:
                    # Name is taken, generate a new one and reconnect
                    new_bot_name=self.generate_bot_name()
                    print_color(f"Name {self.name} is taken, changing to {new_bot_name}", "yellow")
                    self.name = new_bot_name
                    self.close_connection()
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
                #print(f"Network error: {e}")
                self.close_connection()  # Close connection on network error
                break
            except RuntimeError as e:
                self.close_connection()
                #print(f"Connection closed by server: {e}")
                break
        else:
            self.close_connection()

    def close_connection(self):
        #print("Server disconnected, attempting to close connection and restart broadcasting...")
        self.running = False  # Stop the client's operations temporarily to reset connections

        try:
            if self.tcp_socket is not None:
                self.tcp_socket.close()
                # print("TCP socket closed successfully.")
        except socket.error as e:
            print_color(f"Error closing TCP socket: {e}", "red")
        except Exception as e:
            print_color(f"Unexpected error when closing TCP socket: {e}", "red")
        finally:
            self.tcp_socket = None  # Ensure the socket is reset

        # Properly close the UDP socket before re-initializing it
        try:
            if self.udp_socket is not None:
                self.udp_socket.close()
                # print("UDP socket closed successfully.")
        except socket.error as e:
            print_color(f"Error closing UDP socket: {e}", "red")
        except Exception as e:
            print(f"Unexpected error when closing UDP socket: {e}", "red")

        # Reinitialize the UDP socket
        try:
            self.udp_socket.close()
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.udp_socket.bind((SERVER_ADDRESS, UDP_PORT))
            # print("UDP socket reinitialized successfully.")
        except socket.error as e:
            print_color(f"Error reinitializing UDP socket: {e}", "red")
            return  # Stop attempting to restart if socket initialization fails

        # Attempt to restart the server activities
        try:
            self.running = True
            print_color("Server disconnected, listening for offer requests....", "blue")
            self.listen_to_broadcast()  # Restart listening for UDP broadcasts
        except Exception as e:
            #print(f"Error restarting broadcast listening: {e}")
            self.running = False  # Ensure the client does not continue in an erroneous state

    # def close_connection(self):
    #     print("Server disconnected, listening for offer requests...")
    #     self.running = False
    #     self.tcp_socket.close()
    #     self.tcp_socket = None  # Reset the socket
    #     self.running = True
    #     self.listen_to_broadcast()  # Restart listening for UDP broadcasts





