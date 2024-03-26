from Client import TriviaClient
from Server import TriviaServer

if __name__ == "__main__":
    server=TriviaServer()
    server.start()
    client=TriviaClient("barak")
    client.start()
    client=TriviaClient("amit")
    client.start()

