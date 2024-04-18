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
#CLIENT_RESPONSE_TIMEOUT = 13  # in seconds
GAME_DURATION = 10  # in seconds
WAIT_FOR_CLIENT_ANSWER_IN_ROUND= 10
WAIT_FOR_2_CLIENTS_AT_LEAST = 25

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
        self.game_inactive_players = []
        self.get_answer=False
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
        self.starting_port = TCP_PORT




    def start(self, start_time=time.time()):
        self.running=True
        game_start_time = datetime.now()
        logging.info(f"Game started at {game_start_time}")
        self.tcp_socket.listen(5)  # Listen for incoming connections
        print(f"Server started, listening on IP address {self.udp_socket.getsockname()[0]}...\n")
        threading.Thread(target=self.broadcast_message).start()
        threading.Thread(target=self.wait_for_clients(start_time)).start()

    def broadcast_message(self):
        while True:
            # UDP Broadcast the message to all devices on the network
            broadcast_address = ('<broadcast>', UDP_PORT)
            message = struct.pack("!Ib32sH", MAGIC_COOKIE, 0x2, self.padded_server_name.encode('utf-8'), self.find_available_port())
            self.udp_socket.sendto(message, broadcast_address)
            if not self.running:  # Add a condition to stop if server stops running
                break
            time.sleep(1)
            # Sleep for a short duration to avoid flooding the network

    def wait_for_clients(self, start_time=time.time()):
        threads= []
        #start_time = time.time()
        # every conected thread(client) start the 10 sec from the begining
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
                if time.time() - start_time >= GAME_DURATION and len(self.clients) >= 2:
                    self.running = False
                    self.start_game()
                elif time.time() - start_time >= WAIT_FOR_2_CLIENTS_AT_LEAST and len(self.clients) == 1:
                    self.cancel_game_due_to_insufficient_players()
            except Exception as e:
                logging.error(f"An error occurred while accepting new connections: {e}")
                print(f"An error occurred while accepting new connections: {e}")

    def handle_tcp_client(self, conn, addr):
        try:
            data = conn.recv(1024)
            if data:
                team_name = data.decode('utf-8').strip()
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
            else:
                # Handle the case where no data is received i.e., potential data corruption or empty message
                logging.error(f"No data received from {addr[0]}. Connection might be corrupt.")
                conn.close()
        except socket.error as e:
            logging.error(f"Socket error with {addr[0]}: {e}")
            self.remove_client(conn, team_name)
        except UnicodeDecodeError as e:
            # Specifically catches errors that occur during data decoding, which helps in identifying corrupt or improperly formatted data.
            logging.error(f"Decoding error with data from {addr[0]}: {e}")
            self.remove_client(conn, team_name)
        except Exception as e:
            logging.error(f"Unexpected error handling client {addr}: {e}")
            self.remove_client(conn, team_name)  # Safely remove client on error

    def start_game(self):
        try:
            round = 1
            while len(self.clients) > 1:
                self.get_answer = False
                start_time = time.time()
                true_statement = random.choice(TRUE_STATEMENTS)
                false_statement = random.choice(FALSE_STATEMENTS)
                true_false = (true_statement, false_statement)
                if round == 1:
                    logging.info(f"Start new game at {datetime.now()}")
                    message = f"Welcome to the {self.server_name}, where we are answering trivia questions about NBA.\n"
                    counter = 1
                    for client in self.clients:
                        message += f"Player {counter} : {client[0]}\n"
                        counter += 1
                    message += f" == \n"
                else:
                    player_names = " and ".join(client[0] for client in self.clients)
                    message = f"Round {round}, played by {player_names}:\n"

                stat = random.choice(true_false)
                message += f"True or False: {stat}\nEnter your answer (T/F):\n"
                logging.info(f"The asked question of round {round} is {stat}")
                print(message)
                # Send the welcome message to all clients
                threads = []
                for client in self.clients:
                    name, conn = client
                    try:
                        message_to_send = f"{name}\n{message}\n"
                        conn.sendall(message_to_send.encode('utf-8'))
                        thread = threading.Thread(target=self.handle_client_answer, args=(conn, stat, name))
                        thread.start()
                        threads.append(thread)
                    except Exception as e:
                        logging.error(f"Error sending data to client {name}: {e}")
                        print(f"Error sending data to client {name}: {e}")

                for thread in threads:
                    thread.join()
                # Wait for client answers or timeout
                time.sleep(GAME_DURATION)
                if not self.get_answer:
                    logging.info(f"No one answered at round {round}. Preparing another question...")
                    print("No one answered. Preparing another question...")
                    for name, conn in self.clients:
                        try:
                            logging.info(f"sending message to client about no answer at {datetime.now()}")
                            conn.sendall("No one answered. Preparing another question....\n".encode('utf-8'))
                        except Exception as e:
                            logging.error(f"Error notifying client {name}: {e}")
                            print(f"Error notifying client {name}: {e}")

                    # notify all inactive players to prevent clients disconnect from server - bug 1 fixec
                    for client in self.game_inactive_players:  # Ensure all inactive players get updated
                        name, conn = client
                        try:
                            logging.info(f"sending demo message to inactive client {name} at {datetime.now()}")
                            conn.sendall(f"Round {round+1} but you are out of the game.\n".encode('utf-8'))
                        except Exception as e:
                            logging.error(f"Error notifying inactive client {name}: {e}")
                            print(f"Error notifying inactive client {name}: {e}")
                    round += 1
                    continue
                correct_clients = [client for client in self.clients if client[0] in self.correct_answers]
                incorrect_clients = [client for client in self.clients if client[0] not in self.correct_answers]
                self.game_inactive_players.extend(incorrect_clients)


                if incorrect_clients and not correct_clients:  # If all answered incorrectly, do not remove them
                    logging.info(f"All players answered incorrectly at round {round}. Preparing another question...")
                    print("All players answered incorrectly. Preparing another question...")
                    for name, conn in incorrect_clients:
                        try:
                            conn.sendall("Everyone was wrong. Let's try another question.\n".encode('utf-8'))
                        except Exception as e:
                            logging.error(f"Error notifying client {name}: {e}")
                            print(f"Error notifying client {name}: {e}")
                    round+= 1
                    continue
                else:  # Some players were correct, remove incorrect players
                    for name, conn in incorrect_clients:
                        try:
                            logging.info(f"Sending message to client {name} about incorrect answer at {datetime.now()}")
                            conn.sendall("You answered incorrectly and are out of the game.\n".encode('utf-8'))
                        except Exception as e:
                            logging.info(f"Error notifying client {name}: {e}")
                            print(f"Error notifying client {name}: {e}")

                self.clients = correct_clients  # Update the client list to only those who answered correctly


                correct_answer = len(correct_clients) > 0
                if correct_answer:
                    print("At least one player answered correctly.")
                    self.correct_answers = []
                else:
                    print("No one answered correctly. Choosing another random question...")
                    self.correct_answers = []
                round += 1


            else:  # Ending the game
                if len(self.clients) == 1:
                    winner_message=f"Congratulations to the winner: {self.clients[0][0]}.\n"
                    print(winner_message)
                    logging.info(winner_message)
                    for client_name, socket_obj in self.origin_clients:
                        try:
                            socket_obj.sendall(winner_message.encode('utf-8'))
                            self.remove_client(socket_obj, client_name)
                        except ConnectionResetError as e:
                            logging.error(f"Connection with {client_name} reset by peer: {e}")
                            self.remove_client(socket_obj, client_name)
                        #print(f"Closing session for {client_name}\n")
                        # add error handling in case of fail close
                        print(f"Session for {client_name} closed successfully")
                else:
                    no_winner_message = "Game over! No winner.\n"
                    print(no_winner_message)
                    logging.info(no_winner_message)
                    for client_name, socket_obj in self.origin_clients:
                        try:
                            socket_obj.sendall(no_winner_message.encode('utf-8'))
                            self.remove_client(socket_obj, client_name)
                        except ConnectionResetError as e:
                            logging.error(f"Connection with {client_name} reset by peer: {e}")
                            self.remove_client(socket_obj, client_name)
                        #print(f"Closing session for {client_name}\n")
                        # add error handling in case of fail close
                        print(f"Session for {client_name} closed successfully")
                for client in self.clients:
                    client[1].close()  # Close each client's TCP connection
                print("Game over, sending out offer requests...")
                # init all the variables for the next game
                self.game_inactive_players = []
                self.origin_clients = []
                self.clients = []
                self.get_answer = False
                self.running = False
                #self.broadcast_message()  # Assume this method handles broadcasting
                self.start(time.time())
        except Exception as e:
            logging.error("Unexpected error during game start: {}".format(e))


    def handle_client_answer(self, conn, stat, client_name):
        conn.settimeout(GAME_DURATION)  # Set timeout to GAME_DURATION for this client
        try:
            while True:
                try:
                    ans = conn.recv(1024).decode('utf-8').strip()  # Receive answer from client
                except socket.timeout:
                    logging.info(f"Timeout occurred for {client_name}, no response received.")
                    break  # Exit the loop, treat as no response

                # Log the received time for the answer
                received_time = datetime.now()
                logging.info(f"Received answer '{ans}' from {client_name} at {received_time}")
                self.get_answer = True

                # Check if the answer is valid
                if ans.lower() in ("y", "t", "1", "f", "n", "0"):
                    if ((ans.lower() in ("y", "t", "1") and stat in TRUE_STATEMENTS) or
                            (ans.lower() in ("n", "f", "0") and stat in FALSE_STATEMENTS)):
                        print(f"{client_name} is correct!")
                        logging.info(f"{client_name} is correct with the answer of {ans}!")
                        self.correct_answers.append(client_name)
                        break  # Exit the loop as the client gave a correct response
                    else:
                        logging.info(f"{client_name} is incorrect the answer of {ans}!")
                        print(f"{client_name} is incorrect!")
                        break  # Exit the loop as the client gave an incorrect but valid response
                else:
                    print("Invalid input. Please send 'T' or 'F'.")
                    conn.sendall(
                        "Invalid input. Please send 'T' or 'F'.\n".encode('utf-8'))  # Prompt for correct input
        except Exception as e:
            logging.error(f"Error while receiving answer from {client_name}: {e}")
            self.remove_client(conn, client_name)
            # handle_client the case of no one answered

    def remove_client(self, conn, client_name):
        conn.close()
        self.clients = [(name, sock) for name, sock in self.clients if sock != conn]
        self.origin_clients = [(name, sock) for name, sock in self.origin_clients if sock != conn]
        print(f"Disconnected: {client_name} has been removed from the game.")
        logging.info(f"Disconnected: {client_name} has been removed from the game.")

    def cancel_game_due_to_insufficient_players(self):
        if self.clients:
            client_name, client_conn = self.clients[0]  # Correctly unpack the tuple
            try:
                logging.info(f"Only one player connected, game canceled.")
                client_conn.sendall("Only one player connected, game canceled.\n".encode('utf-8'))
                client_conn.close()  # Use the connection object directly
            except Exception as e:
                logging.error(f"Error closing connection for {client_name}: {e}")
        self.running = False
        logging.info("Game canceled due to insufficient players.")
        print("Game canceled due to insufficient players.")

    def find_available_port(self,max_attempts=50):
        for attempt in range(max_attempts):
            try:
                # Create a TCP/IP socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # Try to bind the socket to the port
                sock.bind(('localhost', self.starting_port + attempt))
                # If successful, return the port number
                return self.starting_port + attempt
            except socket.error as e:
                logging.info(f"Port {self.starting_port + attempt} is in use. error info {e}")
                print(f"Port {self.starting_port + attempt} is in use.")
            finally:
                # Ensure that the socket is closed
                sock.close()
        logging.error("Could not find an available port within the range.")
        raise Exception("Could not find an available port within the range.")

# to complete:
# 1. handle a case of a client that disconnects in the middle of the game due to network error
# 2. handle case how to handle a player that didnt answer in a current round
# 3. fix bugs
# 4. consider to change the choose port 5555 function
# 5. verify the busy wait
# sub missions:
# 1. fix bot behavior error handling
# 2. test error handling: data corruption and empty message
# 3. add more logging - V
# 4. add more comments -
# 5. add more exception handling -
# 6. add more print statements/delete unnecessary prints -
# 7. details about our mechanisms for each case


# bugs
# 1. wait 20seconds and not 10sec before telling players that no one answered

# mechanisms:
# 1. if no answer from the server, the client has timeout of SERVER_NO_RESPONSE_TIMEOUT
# 2. if only one player is connected, the server will wait WAIT_FOR_2_CLIENTS_AT_LEAST and then cancel the game

# Done
# 1 send message to the client that the game is canceled - bug 1 fixed
# 2 fix bot generating T,F if already deleted from the game - bug 2 fixed
# 3. if port 5555 is taken, the server will try to bind to the next available port
# 4. step 8 from the assignment - send broadcast only or ready to play game again? now the server ready start game again and send broadcast
# 5. step 9 from the assignment





    # def handle_client_answer(self, conn, stat, client_name):
    #     try:
    #         while True:
    #             ans = conn.recv(1024).decode('utf-8').strip()  # Receive answer from client
    #             # Check if the answer is valid
    #             received_time = datetime.now()
    #             logging.info(f"Received answer '{ans}' from {client_name} at {received_time}")
    #             if ans.lower() in ("y", "t", "1", "f", "n", "0"):
    #                 if ((ans.lower() in ("y", "t", "1") and stat in TRUE_STATEMENTS) or
    #                         (ans.lower() in ("n", "f", "0") and stat in FALSE_STATEMENTS)):
    #                     print(f"{client_name} is correct!")
    #                     logging.info(f"{client_name} is correct!")
    #                     self.correct_answers.append(client_name)
    #                     break  # Exit the loop as the client gave a correct response
    #                 else:
    #                     logging.info(f"{client_name} is incorrect!")
    #                     print(f"{client_name} is incorrect!")
    #                     break  # Exit the loop as the client gave an incorrect but valid response
    #             else:
    #                 print("Invalid input. Please send 'T' or 'F'.")
    #                 conn.sendall("Invalid input. Please send 'T' or 'F'.\n".encode('utf-8'))  # Prompt for correct input
    #     except Exception as e:
    #         logging.error(f"Error while receiving answer from {client_name}: {e}")
    #         self.remove_client(conn, client_name)

# def start_game(self):
#     round = 1
#     while len(self.clients) > 1:
#         start_time = time.time()
#         true_statement = random.choice(TRUE_STATEMENTS)
#         false_statement = random.choice(FALSE_STATEMENTS)
#         true_false = (true_statement, false_statement)
#         if round== 1:
#             message = f"Welcome to the {self.server_name}, where we are answering trivia questions about NBA. \n"
#             counter = 1
#             for client in self.clients:
#                 message += f"Player {counter} : {client[0]}\n"
#                 counter += 1
#             message += f" == \n"
#             stat=random.choice(true_false)
#
#             message += f"True or False: {stat}\nEnter your answer (T/F):\n"
#         else: # If it's not the first round
#             player_names = " and ".join(client[0] for client in self.clients)
#             message = f"Round {round}, played by {player_names}:\n"
#             stat = random.choice(true_false)
#             message += f"True or False: {stat}\nEnter your answer (T/F):\n"
#         logging.info(f"The asked question of round {round} is {stat}")
#         print(message)
#         # Send the welcome message to all clients
#         threads = []
#         for client in self.clients:
#             name, conn = client
#             try:
#                 message_to_send = f"{name}\n{message}\n"  # Ensure each message ends with a newline
#                 conn.sendall(message_to_send.encode('utf-8'))  # Send the name and the message
#                 #threading.Thread(target=conn.sendall, args=(message_to_send.encode('utf-8'))).start()
#                 # self.handle_client_answer(conn, stat, name)
#                 thread = threading.Thread(target=self.handle_client_answer, args=(conn, stat, name))
#                 thread.start()  # Start the thread without immediately joining it
#                 threads.append(thread)
#             except Exception as e:
#                 print(f"Error sending data to client {name}: {e}")
#         for thread in threads:
#             thread.join()  # Join each thread
#         # Wait for client answers or timeout
#         time.sleep(GAME_DURATION)
#         correct_clients = [client for client in self.clients if client[0] in self.correct_answers]
#         incorrect_clients = [client for client in self.clients if client[0] not in self.correct_answers]
#         for name, conn in incorrect_clients:
#             try:
#                 conn.sendall("You answered incorrectly and are out of the game.\n".encode('utf-8'))
#             except Exception as e:
#                 logging.error(f"Error notifying client {name}: {e}")
#                 print(f"Error notifying client {name}: {e}")
#         self.clients = correct_clients
#         correct_answer = False
#         for client in self.clients:
#             name, _ = client
#             # Check if the client answered correctly
#             if name in self.correct_answers:
#                 correct_answer = True
#                 print(f"At least one player answered correctly.")
#                 self.correct_answers = []
#                 #self.start_game()
#                 break
#         # If nobody answered correctly, or no one answered at all, choose another random question
#         if not correct_answer:
#             print("No one answered correctly. Choosing another random question...")
#             self.correct_answers = []
#             #self.start_game()  # Start a new game
#         round += 1
#     else:
#         if len(self.clients) == 1:
#             winner_message=f"Game over! The winner is {self.clients[0][0]}.\n"
#             print(winner_message)
#             logging.info(winner_message)
#             for client_name, socket_obj in self.origin_clients:
#                 socket_obj.sendall(winner_message.encode('utf-8'))
#                 self.remove_client(socket_obj, client_name)
#                 #print(f"Closing session for {client_name}\n")
#                 # add error handling in case of fail close
#                 print(f"Session for {client_name} closed successfully")
#         else:
#             no_winner_message = "Game over! No winner.\n"
#             print(no_winner_message)
#             logging.info(no_winner_message)
#             for client_name, socket_obj in self.origin_clients:
#                 socket_obj.sendall(no_winner_message.encode('utf-8'))
#                 self.remove_client(socket_obj, client_name)
#                 #print(f"Closing session for {client_name}\n")
#                 # add error handling in case of fail close
#                 print(f"Session for {client_name} closed successfully")


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

# def handle_tcp_client(self, conn, addr):
#     try:
#         team_name = conn.recv(1024).decode('utf-8').strip()
#         if any(team_name == existing_name for existing_name, _ in self.origin_clients):
#             conn.sendall("Name is taken, choose a new one.".encode('utf-8'))
#             conn.close()
#             logging.warning(f"Duplicate name attempt from {addr[0]} denied.")
#             print(f"Duplicate name attempt from {addr[0]} denied.")
#         else:
#             self.clients.append((team_name, conn))  # Store client conn
#             self.origin_clients.append((team_name, conn))
#             logging.info(f"Team {team_name} connected from {addr[0]}")
#             print(f"Team {team_name} connected from {addr[0]}\n")
#     except Exception as e:
#         logging.error(f"Error handling client {addr}: {e}")
#         self.remove_client(conn, team_name)  # Safely remove client on error