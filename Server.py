import socket
import threading
import struct
import random
import time

# Constants
UDP_PORT = 13117
TCP_PORT = 5555
MAGIC_COOKIE = 0xabcddcba
GAME_DURATION = 3  # in seconds
TRUE_STATEMENTS = ["Python is a programming language.", "The sun rises in the east."]
FALSE_STATEMENTS = ["Water boils at 100 degrees Fahrenheit.", "The Earth is flat."]


class TriviaServer:
    def __init__(self):
        self.running = True
        self.origin_clients = []
        self.clients = []
        self.correct_answers = []
        self.server_name = "AwesomeTriviaServer"
        # To Make sure this field is always 32 characters long even if your server name is shorter.
        self.padded_server_name = self.server_name.ljust(32)[:32]
        # define UDP socket
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind(('0.0.0.0', UDP_PORT))
        # define TCP socket
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(('0.0.0.0', TCP_PORT))




    def start(self):
        self.tcp_socket.listen(5)  # Listen for incoming connections
        print(f"Server started, listening on IP address {self.udp_socket.getsockname()[0]}...\n")

        threading.Thread(target=self.broadcast_message).start()
        threading.Thread(target=self.wait_for_clients).start()

    def broadcast_message(self):
        while True:
            # UDP Broadcast the message to all devices on the network
            broadcast_address = ('<broadcast>', UDP_PORT)
            message = struct.pack("!Ib32sH", MAGIC_COOKIE, 0x2, self.padded_server_name.encode('utf-8'), TCP_PORT)
            self.udp_socket.sendto(message, broadcast_address)
            # Sleep for a short duration to avoid flooding the network
            time.sleep(1)  # You can adjust the sleep duration as needed

    def wait_for_clients(self):
        threads= []
        start_time = time.time()
        self.tcp_socket.settimeout(GAME_DURATION)
        while self.running:
            try:
                conn, tcp_addr = self.tcp_socket.accept()  # Accept TCP connection
                thread=threading.Thread(target=self.handle_tcp_client, args=(conn, tcp_addr))
                threads.append(thread)# Add the thread to the list
                thread.start()  # Join each thread
            except socket.timeout:
                if time.time() - start_time >= GAME_DURATION:
                    self.running = False
                    self.start_game()
            # for thread in threads:
            #     thread.join()

    def handle_tcp_client(self, conn, addr):

        team_name = conn.recv(1024).decode('utf-8').strip()
        self.clients.append((team_name, conn))  # Store client conn
        self.origin_clients.append((team_name, conn))
        print(f"Team {team_name} connected from {addr[0]}\n")


    def start_game(self):

        while len(self.clients) > 0:
            start_time = time.time()
            true_statement = random.choice(TRUE_STATEMENTS)
            false_statement = random.choice(FALSE_STATEMENTS)
            true_false = (true_statement, false_statement)

            # Build the welcome message
            message = f"Welcome to the {self.server_name}, where we are answering trivia questions about NBA. \n"
            counter = 1
            for client in self.clients:
                message += f"Player {counter} : {client[0]}\n"
                counter += 1
            message += f" == \n"
            stat=random.choice(true_false)
            message += f"True or False: {stat}\n"
            print(message)
            # Send the welcome message to all clients
            threads = []
            for client in self.clients:
                name, conn = client
                try:
                    message_to_send = f"{name}\n{message}\n"  # Ensure each message ends with a newline
                    conn.sendall(message_to_send.encode('utf-8'))  # Send the name and the message
                    #threading.Thread(target=conn.sendall, args=(message_to_send.encode('utf-8'))).start()
                    # self.handle_client_answer(conn, stat, name)
                    thread = threading.Thread(target=self.handle_client_answer, args=(conn, stat, name))
                    thread.start()  # Start the thread without immediately joining it
                    threads.append(thread)
                except Exception as e:
                    print(f"Error sending data to client {name}: {e}")
            for thread in threads:
                thread.join()  # Join each thread
            self.clients = [client for client in self.clients if client[0] in self.correct_answers]
            # Wait for client answers or timeout
            time.sleep(GAME_DURATION)
            correct_answer = False
            for client in self.clients:
                name, _ = client
                # Check if the client answered correctly
                if name in self.correct_answers:
                    correct_answer = True
                    print(f"At least one player answered correctly.")
                    self.correct_answers = []
                    #self.start_game()
                    break

            # If nobody answered correctly, or no one answered at all, choose another random question
            if not correct_answer:
                print("No one answered correctly. Choosing another random question...")
                self.correct_answers = []
                #self.start_game()  # Start a new game
        else:
            print("Game over! No players left.")
            for client_name, socket_obj in self.origin_clients:
                print(f"Closing session for {client_name}")
                socket_obj.close()
                print(f"Session for {client_name} closed successfully")

    def handle_client_answer(self, conn,stat,client_name):
        try:
            ans = conn.recv(1024).decode('utf-8').strip()  # Receive answer from client
            print(ans)
            # check if the answer is correct
            if (ans.lower()=="y" or ans.lower()=="t" or ans=="1" or ans.lower()=="f" or ans.lower()=="n" or ans=="0"):
                if ((ans.lower() == "y" or ans.lower() == "t" or ans == "1")and stat in TRUE_STATEMENTS) or ((ans.lower() == "n" or ans.lower() == "f" or ans == "0")and stat in FALSE_STATEMENTS):
                    print(f"{client_name} is correct !")
                    self.correct_answers.append(client_name)

                else:
                    print(f"{client_name} is incorrect !")

            else:
                print("invalid input")

        except Exception as e:
            print(f"Error while receiving answer from client: {e}")

