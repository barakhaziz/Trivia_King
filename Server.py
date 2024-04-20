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
WAIT_FOR_CLIENT_ANSWER_IN_ROUND = 10
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

class TriviaServer:
    def __init__(self):
        self.running = True
        self.origin_clients = []
        self.game_characters = []
        self.clients_didnt_answer = []
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
        self.running = True
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
            time.sleep(1.3)
            # Sleep for a short duration to avoid flooding the network

    def wait_for_clients(self, start_time=time.time()):
        threads = []
        #start_time = time.time()
        # every conected thread(client) start the 10 sec from the begining
        self.tcp_socket.settimeout(GAME_DURATION)
        while self.running:
            try:
                conn, tcp_addr = self.tcp_socket.accept()  # Accept TCP connection
                logging.info(f"New client {tcp_addr[0]} connected.")
                thread = threading.Thread(target=self.handle_tcp_client, args=(conn, tcp_addr))
                threads.append(thread)# Add the thread to the list
                thread.start()  # Join each thread
                time.sleep(1.3)
            except socket.timeout as e:
                logging.error(f"Accepting new client timed out: {e}")
                if time.time() - start_time >= GAME_DURATION and len(self.clients) >= 2:
                    self.running = False
                    self.start_game()
                elif time.time() - start_time >= WAIT_FOR_2_CLIENTS_AT_LEAST and len(self.clients) == 1:
                    self.cancel_game_due_to_insufficient_players()
            except Exception as e:
                logging.error(f"An error occurred while accepting new connections: {e}")
                print_color(f"An error occurred while accepting new connections: {e}", "red")
            time.sleep(1.3)

    def handle_tcp_client(self, conn, addr):
        try:
            data = conn.recv(1024)
            if data:
                team_name = data.decode('utf-8').strip()
                if any(team_name == existing_name for existing_name, _ in self.origin_clients):
                    conn.sendall(f"\033[93mName is taken, choose a new one.\033[0m".encode('utf-8'))
                    logging.warning(f"Duplicate name {team_name} attempt from {addr[0]} denied.")
                    print_color(f"Duplicate name attempt from {addr[0]} denied.", "red")
                else:
                    self.clients.append((team_name, conn))  # Store client conn
                    self.origin_clients.append((team_name, conn))
                    logging.info(f"Team {team_name} connected from {addr[0]}")
                    print_color(f"Team {team_name} connected from {addr[0]}\n", "green")
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

    # notify all inactive players to prevent clients disconnect from server
    def notify_inactive_players(self, round):
        for client in self.game_inactive_players:  # Ensure all inactive players get updated
            name, conn = client
            try:
                logging.info(f"sending demo message to inactive client {name} at {datetime.now()}")
                conn.sendall(f"Round {round} but you are out of the game.\n".encode('utf-8'))
            except Exception as e:
                logging.error(f"Error notifying inactive client {name}: {e}")
                print_color(f"Error notifying inactive client {name}: {e}", "red")

    def start_game(self):
        try:
            round = 1
            while len(self.clients) > 1:
                self.get_answer = False
                true_statement = random.choice(TRUE_STATEMENTS)
                false_statement = random.choice(FALSE_STATEMENTS)
                true_false = (true_statement, false_statement)
                if round == 1:
                    logging.info(f"Start new game at {datetime.now()}")
                    message = f"\033[94mWelcome to the {self.server_name}, where we are answering trivia questions about NBA.\n\033[0m"
                    counter = 1
                    for client in self.clients:
                        message += f"Player {counter} : {client[0]}\n"
                        counter += 1
                    message += f" == \n"
                else:
                    player_names = " and ".join(client[0] for client in self.clients)
                    message = f"\033[94mRound {round}\033[0m, played by {player_names}:\n"

                stat = random.choice(true_false)
                message += f"\033[93mTrue or False: {stat}\nEnter your answer (T/F):\n\033[0m"
                logging.info(f"The asked question of round {round} is {stat}")
                round += 1
                print(message)
                # Send the welcome message to all clients
                threads = []
                self.clients_didnt_answer = list(self.clients)
                for client in self.clients:
                    name, conn = client
                    try:
                        message_to_send = f"{name}\n{message}\n"
                        conn.sendall(message_to_send.encode('utf-8'))
                        thread = threading.Thread(target=self.handle_client_answer, args=(conn, stat, name))
                        thread.start()
                        threads.append(thread)
                    except socket.error as e:
                        logging.error(f"Error sending data to client {name}: {e}")
                        self.clients.remove(client)
                        print_color(f"Error sending data to client {name}: {e}", "red")
                    except ConnectionResetError as e:
                        logging.error(f"Connection with {name} reset by peer: {e}")
                        self.clients.remove(client)
                        print_color(f"Connection with {name} reset by peer: {e}", "green")
                    except Exception as e:
                        logging.error(f"Error sending data to client {name}: {e}")
                        self.clients.remove(client)
                        print_color(f"Error sending data to client {name}: {e}", "red")

                time.sleep(3)
                for thread in threads:
                    thread.join()

                #time.sleep(GAME_DURATION)

                # case 1: no one answered in the current round in 10 seconds
                # behavior: notify all players that no one answered and prepare another question
                if self.clients == self.clients_didnt_answer and not self.get_answer:
                    logging.info(f"No one answered at round {round}. Preparing another question...")
                    print_color("No one answered. Preparing another question...", "cyan")
                    for name, conn in self.clients:
                        try:
                            logging.info(f"sending message to client about no answer at {datetime.now()}")
                            conn.sendall("No one answered. Preparing another question....\n".encode('utf-8'))
                        except Exception as e:
                            logging.error(f"Error notifying client - case1 {name}: {e}")
                            print_color(f"Error notifying client - case1 {name}: {e}", "red")
                    self.notify_inactive_players(round)
                    time.sleep(1.3)
                    #round += 1
                    continue
                # case 2: some players didn't answer in the current round
                # assumptions: the player didn't answer because of 2 reasons: 
                # 1. the player disconnected from the game due to network error in his side
                # 2. the player didn't answer in the current round because he didn't know the answer
                # behavior: based on both assumptions, the server will remove the player from the game
                else: # remove player that didn't answer in the current round
                    for name, conn in self.clients_didnt_answer:
                        try:
                            logging.info(f"Sending message to client {name} about no answer at {datetime.now()}")
                            conn.sendall("\033[91mYou didn't answer in the current round and are out of the game.\n\033[0m".encode('utf-8'))
                            self.remove_client(conn, name)
                        except socket.error as e:
                            # This exception handles the case where the socket is already closed or unreachable
                            logging.error(f"Client {name} disconnected from the game due the network error: {e}")
                            print_color(f"Client {name} disconnected from the game due the network error: {e}", "red")
                        except Exception as e:
                            logging.error(f"Unexpected error when trying to close connection with {name}: {e}")
                            print_color(f"Unexpected error when trying to close connection with {name}: {e}", "red")
                    time.sleep(1.3)
                    #round += 1



                # maybe replace using set instead of list
                correct_clients = [client for client in self.clients if client[0] in self.correct_answers]
                incorrect_clients = [client for client in self.clients if client[0] not in self.correct_answers and client[0] not in self.clients_didnt_answer]
                self.game_inactive_players.extend(incorrect_clients)

                # for debug only
                # print(f"correct_answers: {self.correct_answers}")
                # print(f"correct_clients: {correct_clients}")
                # print(f"incorrect_clients: {incorrect_clients}")
                # print(f"client which didnt answer: {self.clients_didnt_answer}")

                # case 7: one player answered incorrectly and the other didn't answer
                # behavior: game over without a winner
                if len(incorrect_clients) == 1 and len(correct_clients) == 0 and len(self.clients_didnt_answer) + len(incorrect_clients) == len(self.clients):
                    incorrect_clients[0][1].sendall("\033[91mYou answered incorrectly and are out of the game.\n\033[0m".encode('utf-8'))
                    self.clients = []
                    time.sleep(1.3)
                    continue

                # case 3: all players answered incorrectly
                # behavior: notify all players that all answered incorrectly and prepare another question
                if incorrect_clients and not correct_clients and len(incorrect_clients) > 1:  # If all answered incorrectly, do not remove them
                    logging.info(f"All players answered incorrectly at round {round}. Preparing another question...")
                    print_color("All players answered incorrectly. Preparing another question...","magenta")
                    for name, conn in incorrect_clients:
                        try:
                            conn.sendall("Everyone was wrong. Let's try another question.\n".encode('utf-8'))
                        except Exception as e:
                            logging.error(f"Error notifying client - case2 {name}: {e}")
                            print_color(f"Error notifying client - case2 {name}: {e}", "red")
                    time.sleep(1.3)
                    #round += 1
                    continue

                # case 4: at least one player answered correctly
                # behavior: notify all players that at least one player answered correctly and prepare another question
                else:  # Some players were correct, remove incorrect players
                    for name, conn in incorrect_clients:
                        try:
                            logging.info(f"Sending message to client {name} about incorrect answer at {datetime.now()}")
                            conn.sendall("\033[91mYou answered incorrectly and are out of the game.\n\033[0m".encode('utf-8'))
                        except Exception as e:
                            logging.info(f"Error notifying client - case3 {name}: {e}")
                            print_color(f"Error notifying client- case3 {name}: {e}", "red")
                    time.sleep(1.3)
                    #round += 1

                self.clients = correct_clients  # Update the client list to only those who answered correctly
                self.correct_answers= []  # Reset the correct answers list


            # handle game end: there are less then 2 players in the game
            else:
                # case 5: only one player left in the game
                # behavior: notify all players who is the winner and close the sockets with all the players
                if len(self.clients) == 1:
                    winner_message=f"Game over!\nCongratulations to the winner: {self.clients[0][0]}.\n"
                    print_color(winner_message, "white")
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
                        print_color(f"Session for {client_name} closed successfully", "green")

                # case 6: no one left in the game (no players)
                # behavior: notify all players that there is no winner and close the sockets with all the players
                else:
                    no_winner_message = "Game over! No winner.\n"
                    #print(self.game_characters)
                    print_color(no_winner_message, "white")
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
                        print_color(f"Session for {client_name} closed successfully", "green")

                for client in self.clients:
                    client[1].close()  # Close each client's TCP connection
                print_color("Game over, sending out offer requests...", "cyan")

                #init all the variables for the next game
                log_file_path = 'server.log'
                winner, wins = self.find_top_winner(log_file_path)
                most_common_question, occurrence = self.find_most_common_question(log_file_path)
                most_common_answer, count = self.find_most_common_answer(log_file_path)
                print("Application Statistics")
                print_color(f"The client with the most wins is {winner} with {wins} wins.","blue")
                print_color(f"The most common answer was '{most_common_answer}' with {count} occurrences.","blue")
                print_color(f"The most common question was: '{most_common_question}' asked {occurrence} times.","blue")
                self.init_struct_for_new_game()

        except Exception as e:
            logging.error("Unexpected error during game start: {}".format(e))


    def init_struct_for_new_game(self):

        self.game_inactive_players = []
        self.origin_clients = []
        self.clients_didnt_answer = []
        self.clients = []
        self.get_answer = False
        self.running = False
        self.game_characters = []
        self.correct_answers = []
        self.start(time.time())
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
                self.game_characters.append(ans)

                # Check if the answer is valid
                if ans.lower() in ("y", "t", "1", "f", "n", "0"):
                    if ((ans.lower() in ("y", "t", "1") and stat in TRUE_STATEMENTS) or
                            (ans.lower() in ("n", "f", "0") and stat in FALSE_STATEMENTS)):
                        print_color(f"{client_name} is correct!", "cyan")
                        logging.info(f"{client_name} is correct with the answer of {ans}!")
                        self.correct_answers.append(client_name)
                        self.clients_didnt_answer.remove((client_name, conn))
                        break  # Exit the loop as the client gave a correct response
                    else:
                        logging.info(f"{client_name} is incorrect the answer of {ans}!")
                        print_color(f"{client_name} is incorrect!", "magenta")
                        self.clients_didnt_answer.remove((client_name, conn))
                        break  # Exit the loop as the client gave an incorrect but valid response
                else:
                    print_color("Invalid input. Please send 'T' or 'F'.", "red")
                    conn.sendall(
                        "\033[91mInvalid input. Please send 'T' or 'F'.\n\033[0m".encode('utf-8'))  # Prompt for correct input
                time.sleep(1.3)
        except Exception as e:
            logging.error(f"Error while receiving answer from {client_name}: {e}")
            self.remove_client(conn, client_name)
            # handle_client the case of no one answered

    def remove_client(self, conn, client_name):
        conn.close()
        self.clients = [(name, sock) for name, sock in self.clients if sock != conn]
        self.origin_clients = [(name, sock) for name, sock in self.origin_clients if sock != conn]
        #print_color(f"Disconnected: {client_name} has been removed from the game.", "red")
        logging.info(f"Disconnected: {client_name} has been removed from the game.")

    def cancel_game_due_to_insufficient_players(self):
        if self.clients:
            client_name, client_conn = self.clients[0]  # Correctly unpack the tuple
            try:
                logging.info(f"Only one player connected, game canceled.")
                client_conn.sendall("\033[91mOnly one player connected, game canceled.\n\033[0m".encode('utf-8'))
                client_conn.close()  # Use the connection object directly
            except Exception as e:
                logging.error(f"Error closing connection for {client_name}: {e}")
        self.running = False
        logging.info("Game canceled due to insufficient players.")
        print_color("Game canceled due to insufficient players.", "red")

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
                print_color(f"Port {self.starting_port + attempt} is in use.", "red")
            finally:
                # Ensure that the socket is closed
                sock.close()
        logging.error("Could not find an available port within the range.")
        raise Exception("Could not find an available port within the range.")

    def find_top_winner(self, log_file_path):
        import re
        from collections import defaultdict

        winner_regex = re.compile(r"Congratulations to the winner: (\S+)")
        win_count = defaultdict(int)

        try:
            with open(log_file_path, 'r') as file:
                for line in file:
                    match = winner_regex.search(line)
                    if match:
                        winner = match.group(1)
                        win_count[winner] += 1

            if not win_count:
                return "No winners found", 0
            top_winner = max(win_count, key=win_count.get)
            return top_winner, win_count[top_winner]
        except Exception as e:
            logging.error(f"Failed to read log file or find top winner: {e}")
            return "Error finding winner", 0

    def find_most_common_answer(self, log_file_path):
        import re
        from collections import defaultdict
        from collections import Counter

        # Updated regex to capture answers and who answered them
        answer_regex = re.compile(r"Received answer '(\w)' from (\S+) at")
        answer_count = defaultdict(int)

        try:
            with open(log_file_path, 'r') as file:
                for line in file:
                    match = answer_regex.search(line)
                    if match:
                        answer = match.group(1)  # Capture the answer provided
                        answer_count[answer] += 1

            if not answer_count:
                return "No answers found", 0
            # Using Counter to find the most common answer
            most_common_answer, count = Counter(answer_count).most_common(1)[0]
            return most_common_answer, count
        except Exception as e:
            logging.error(f"Failed to read log file or find the most common answer: {e}")
            return "Error finding the most common answer", 0

    def find_most_common_question(self, log_file_path):
        import re
        from collections import defaultdict, Counter
        import logging

        # Regex pattern to extract the question asked in each round
        question_regex = re.compile(r"The asked question of round \d+ is (.+)$")
        question_count = defaultdict(int)

        try:
            with open(log_file_path, 'r') as file:
                for line in file:
                    match = question_regex.search(line)
                    if match:
                        question = match.group(1).strip()
                        question_count[question] += 1

            if not question_count:
                return "No questions found", 0
            most_common_question, count = Counter(question_count).most_common(1)[0]
            return most_common_question, count
        except Exception as e:
            logging.error(f"Failed to read log file or find the most common question: {e}")
            return "Error finding the most common question", 0

# TOP PRIORITY TASKS FOR ALL OF US!
# 1. check the assignment requirements again! every step, everyone by its own!
# 1. בעברית שיהיה ברור: שכל אחד יעבור על כל דרישות העבודה לוודא שכלום לא פוספס
# 2. In your time, run all cases again to identify more bugs
# 3. verify there is no busy waiting in the code, and no 1% usage of the CPU - Barak


# sub missions:
# 1. fix bot behavior error handling
# 2. test error handling: data corruption and empty message
# 3. add more comments to the code
# 4. add more exception handling both client and server
# 5. add more print statements/delete unnecessary prints
# 6. details about our mechanisms for each case
# 7. create readme file in the repository that explain all our assumptions, mechanism and architecture - Amit (V)
# 8. verify case when client was wrong and disconnect due to network error - Oded
# 9. in case of duplicate name, the client generate new name and connect to the server


# bugs
# clients bugs:
# 1. the client print wired messages: getting 2 broadcast from 2 servers although its the same server(different ips)
# 2. inactive clients prints 2 time the message "round x but you are out of the game" - Amit
# 3. In case client type invalid input for the whole round, the server will do hard remove from the game


# server bugs:
# print the winner with new line: Charlie is correct!\nCharlie Wins! instead Charlie is correct! Charlie Wins!

# FIXED bugs:
# 1. FIXED! handle case of game over: only one player answer incorrectly and the other didn't answer - Amit
# 2. FIXED! the client didn't start listening for offers after the server close connection - Amit
# 3. FIXED! in game with bots, there is no winner in case of one correct answer and all the rest are wrong (basically like 2) - Amit
# 4. FIXED in case of duplicate name, the clients wont stop generating the same name and keep try to connect server - Amit
# 5. FIXED! bot not remove clients from game after first round: test 7 bots client file - Amit


# Nice to have\to consider - please work only if all the bugs are fixed:
# 1. handle case where before game start, the client connect and then disconnect due to network error
# 2. how to identify when client disconnect due to network error or didn't answer
# 3. generate new questions and not hard coded questions, oded suggestion


# Scenarios to test:
# All the cases 1-7
# The server disconnect from the clients by shutdown server and then client back to listening for offers - V
# All the client disconnect from the server by shutdown client and then the server will send broadcast message - V
# When game is over both client and server will disconnect from each other and the server will send broadcast message and client will back to listening for offers - V
# Duplicate client name of non bot client in the game
# Duplicate client name of bot client in the game - V


# Done
# 1 send message to the client that the game is canceled - bug 1 fixed
# 2 fix bot generating T,F if already deleted from the game - bug 2 fixed
# 3. if port 5555 is taken, the server will try to bind to the next available port
# 4. step 8 from the assignment - send broadcast only or ready to play game again? now the server ready start game again and send broadcast
# 5. step 9 from the assignment




# mechanisms:
# 1. server disconnect handling: if no answer from the server, the client has timeout of SERVER_NO_RESPONSE_TIMEOUT
# 2. if only one player is connected, the server will wait WAIT_FOR_2_CLIENTS_AT_LEAST and then cancel the game
# 3. when game ended, the server will send broadcast message to all clients and be ready to start a new game (not just broadcast)
# 4. client disconnect handling: if a player didn't answer in the round, he removed from the game completely - try close it session
