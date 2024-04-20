from Client import TriviaClient
from Server import TriviaServer
import threading
import random

if __name__ == "__main__":
    try:
        server = TriviaServer()
        server.start()
    except KeyboardInterrupt:
        print("Shutdown requested...exiting")
    # except Exception:
    #     traceback.print_exc()
    for thread in threading.enumerate():
        if thread != threading.current_thread():
            thread.join()


