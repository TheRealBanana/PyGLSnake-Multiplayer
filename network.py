import socket
import threading
import time
# Networking stuff for the multiplayer version of PyGlSnake


# I thought about creating a dedicated server daemon and then having each
# game client connect but that was kind of unnecessary. I decided to just
# make each client capable of being both a server and client.
#
#
# By default we will run in server mode and wait for players to connect.
# Once we have at least one client connected we give the option to start
# the game via pressing enter in the server's command line console.
#
# Each client will then be given a countdown in their own console before
# the game starts.
#
#
# For now there is no latency compensation as its assumed each client is
# on the same LAN. In the future a basic form of compensation may be implemented.


class ClientMode(threading.Thread):
    def __init__(self):
        super(ClientMode, self).__init__()
        
        
        
class ServerMode(threading.Thread):
    def __init__(self):
        super(ClientMode, self).__init__()
        
        
class ServerClientConnection(threading.Thread):
    def __init__(self):
        super(ClientMode, self).__init__()