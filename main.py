from Client import TriviaClient
from Server import TriviaServer
import threading

if __name__ == "__main__":
    server=TriviaServer()
    server.start()
    client=TriviaClient("barak")
    client.start()
    client=TriviaClient("amit")
    client.start()
    for thread in threading.enumerate():
        if thread != threading.current_thread():
            thread.join()


