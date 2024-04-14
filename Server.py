import socket
import threading
import struct
import random
import time
import logging
from datetime import datetime
# Constants
UDP_PORT = 13117
TCP_PORT = 5555
MAGIC_COOKIE = 0xabcddcba
GAME_DURATION = 5  # in seconds

# Initialize logging
logging.basicConfig(filename='server.log', level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')
TRUE_STATEMENTS = [
    "Michael Jordan won 6 NBA championships.",
    "The Los Angeles Lakers have won 17 NBA championships.",
    "LeBron James was drafted first overall in 2003.",
    "The Boston Celtics have the most NBA championships.",
    "Kobe Bryant spent his entire career with the Los Angeles Lakers.",
    "Tim Duncan won five NBA championships with the San Antonio Spurs.",
    "Shaquille O'Neal won his first NBA championship in 2000.",
    "The Golden State Warriors broke the record for the most wins in a season in 2016.",
    "Dirk Nowitzki is the highest-scoring foreign-born player in NBA history.",
    "The Toronto Raptors won their first NBA Championship in 2019."
]

FALSE_STATEMENTS = [
    "The Chicago Bulls have won 10 NBA championships.",
    "Kareem Abdul-Jabbar scored 100 points in a single NBA game.",
    "The Detroit Pistons have never won an NBA championship.",
    "Michael Jordan was drafted by the Portland Trail Blazers.",
    "The Miami Heat was established in 1970.",
    "Kevin Durant won his first NBA championship with the Oklahoma City Thunder.",
    "The NBA was founded in 1949 as the National Basketball Association.",
    "Allen Iverson won two NBA championships.",
    "The New York Knicks won the NBA Championship in 2012.",
    "LeBron James has never won an NBA MVP award."
]

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
        game_start_time = datetime.now()
        logging.info(f"Game started at {game_start_time}")
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
                logging.info(f"New client {tcp_addr[0]} connected.")
                thread=threading.Thread(target=self.handle_tcp_client, args=(conn, tcp_addr))
                threads.append(thread)# Add the thread to the list
                thread.start()  # Join each thread
            except socket.timeout as e:
                logging.error(f"Accepting new client timed out: {e}")
                if time.time() - start_time >= GAME_DURATION:
                    self.running = False
                    self.start_game()

    def handle_tcp_client(self, conn, addr):
        try:
            team_name = conn.recv(1024).decode('utf-8').strip()
            if any(team_name == existing_name for existing_name, _ in self.origin_clients):
                conn.sendall("Name is taken, choose a new one.".encode('utf-8'))
                conn.close()
                logging.warning(f"Duplicate name attempt from {addr[0]} denied.")
                print(f"Duplicate name attempt from {addr[0]} denied.")
            else:
                self.clients.append((team_name, conn))  # Store client conn
                self.origin_clients.append((team_name, conn))
                logging.info(f"Team {team_name} connected from {addr[0]}")
                print(f"Team {team_name} connected from {addr[0]}\n")
        except Exception as e:
            logging.error(f"Error handling client {addr}: {e}")
            self.remove_client(conn, team_name)  # Safely remove client on error



    def start_game(self):
        round = 1
        while len(self.clients) > 0:
            start_time = time.time()
            true_statement = random.choice(TRUE_STATEMENTS)
            false_statement = random.choice(FALSE_STATEMENTS)
            true_false = (true_statement, false_statement)
            if round== 1:
                message = f"Welcome to the {self.server_name}, where we are answering trivia questions about NBA. \n"
                counter = 1
                for client in self.clients:
                    message += f"Player {counter} : {client[0]}\n"
                    counter += 1
                message += f" == \n"
                stat=random.choice(true_false)
                message += f"True or False: {stat}\n"
            else: # If it's not the first round
                player_names = " and ".join(client[0] for client in self.clients)
                message = f"Round {round}, played by {player_names}:\n"
                stat = random.choice(true_false)
                message += f"True or False: {stat}\n"
            logging.info(f"The asked question of round {round} is {stat}")
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
            round += 1
        else:
            print("Game over! No players left.")
            for client_name, socket_obj in self.origin_clients:
                print(f"Closing session for {client_name}")
                socket_obj.close()
                print(f"Session for {client_name} closed successfully")

    def handle_client_answer(self, conn, stat, client_name):
        try:
            while True:
                ans = conn.recv(1024).decode('utf-8').strip()  # Receive answer from client
                # Check if the answer is valid
                received_time = datetime.now()
                logging.info(f"Received answer '{ans}' from {client_name} at {received_time}")
                if ans.lower() in ("y", "t", "1", "f", "n", "0"):
                    if ((ans.lower() in ("y", "t", "1") and stat in TRUE_STATEMENTS) or
                            (ans.lower() in ("n", "f", "0") and stat in FALSE_STATEMENTS)):
                        print(f"{client_name} is correct!")
                        logging.info(f"{client_name} is correct!")
                        self.correct_answers.append(client_name)
                        break  # Exit the loop as the client gave a correct response
                    else:
                        logging.info(f"{client_name} is incorrect!")
                        print(f"{client_name} is incorrect!")
                        break  # Exit the loop as the client gave an incorrect but valid response
                else:
                    print("Invalid input. Please send 'T' or 'F'.")
                    conn.sendall("Invalid input. Please send 'T' or 'F'.\n".encode('utf-8'))  # Prompt for correct input
        except Exception as e:
            logging.error(f"Error while receiving answer from {client_name}: {e}")
            self.remove_client(conn, client_name)
    def remove_client(self, conn, client_name):
        conn.close()
        self.clients = [(name, sock) for name, sock in self.clients if sock != conn]
        self.origin_clients = [(name, sock) for name, sock in self.origin_clients if sock != conn]
        print(f"Disconnected: {client_name} has been removed from the game.")
        logging.info(f"Disconnected: {client_name} has been removed from the game.")
    # def handle_client_answer(self, conn,stat,client_name):
    #     try:
    #         ans = conn.recv(1024).decode('utf-8').strip()  # Receive answer from client
    #         print(ans)
    #         # check if the answer is correct
    #         if (ans.lower()=="y" or ans.lower()=="t" or ans=="1" or ans.lower()=="f" or ans.lower()=="n" or ans=="0"):
    #             if ((ans.lower() == "y" or ans.lower() == "t" or ans == "1")and stat in TRUE_STATEMENTS) or ((ans.lower() == "n" or ans.lower() == "f" or ans == "0")and stat in FALSE_STATEMENTS):
    #                 print(f"{client_name} is correct !")
    #                 self.correct_answers.append(client_name)
    #
    #             else:
    #                 print(f"{client_name} is incorrect !")
    #
    #         else:
    #             print("invalid input")
    #
    #     except Exception as e:
    #         print(f"Error while receiving answer from client: {e}")


# what we do for invalid input - V
# how handle in case of client disconnet in the middle of the game: save it state or delete it - V