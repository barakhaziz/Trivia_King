from Client import TriviaClient
import threading

def start_client():
    client = TriviaClient(None, True)  # None for name, True for is_bot
    client.start()

if __name__ == "__main__":
    # Create a list to hold the thread objects
    threads = []

    # Number of client bots you want to run
    num_clients = 7

    # Create and start a thread for each client
    for _ in range(num_clients):
        t = threading.Thread(target=start_client)
        t.start()
        threads.append(t)

    # Wait for all threads to complete
    for t in threads:
        t.join()
