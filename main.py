from Client import TriviaClient
from Server import TriviaServer
import threading
import random

if __name__ == "__main__":
    server = TriviaServer()
    server.start()
    # client = TriviaClient("barak")
    # client.start()f
    for thread in threading.enumerate():
        if thread != threading.current_thread():
            thread.join()


# if __name__ == "__main__":
#     bot_name = "BOT:" + str(random.randint(1, 100))  # Generate a unique name for the bot
#     bot_client = TriviaClient(bot_name, is_bot=True)
#     bot_client.start()
