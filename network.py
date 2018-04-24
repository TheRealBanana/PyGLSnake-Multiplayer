import socket
import select
import threading
import time
import queue
import cPickle
from sys import exit as sys_exit

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
    def __init__(self, renderman_instance, quit_socket, server_ip, server_port):
        self.renderman_instance = renderman_instance
        self.server_ip = server_ip
        self.server_port = server_port
        self.quit_socket = quit_socket
        self.main_socket = None
        super(ClientMode, self).__init__()
        
    #Main part of our thread
    def run(self):
        #Try and initialize a connection with our server. If we can't its already over.
        try:
            #Using streaming TCP sockets. UDP is overkill for what we are doing.
            self.main_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.main_socket.connect((self.server_ip, self.server_port))
            
        except:
            print "Error connecting to server at ip %s, exiting..." % self.server_ip
            #sys_exit(1) #This does NOT seem to kill the whole app. We got some 'splainin to do.
            #exit(1)
            raise(Exception("DA FAQ"))
        
        #Ok we have a good connection to the server. Lets listen for any data
        while self.quitting == False:
            data = None
            try:
                readable, _, _ = select.select([self.client_socket, self.quit_socket], [], [], 60) #60 second timeout
                for sock in readable:
                    if sock == self.main_socket:
                        data = self.main_socket.recv(4096)
                        #Handle any commands we get
                        if data is not None and len(data) > 0:
                            self.processess_command(data)
                        continue
                    elif sock == self.quit_socket:
                        self.quit_socket.accept()
                        self.quit_socket.close()
                        self.quitting = True
                        continue
            except:
                break
        
        #Got the message to quit or the thread died, either way lets quit
        self.quit_thread()
    
    
    def process_command(self, rawdata):
        try:
            data = cPickle.loads(rawdata)
            if isinstance(data, list) is False:
                print "Pickled data was not a list, something is horribly wrong here so im quiting..."
                sys_exit()
        except:
            #Major error, blow up
            print "Command processing error, couldn't load pickel data."
            sys_exit()
        
        if data[0] == "GET_NEXT_MOVE":
            #Snake reference here, have to change the entire way snake ticks and works tho. Lame.
            pass
        elif data[0] == "GAME_UPDATE":
            #Get player position data for other clients 
            pass
        elif data[0] == "GAME_START":
            #Game is starting
            pass
        elif data[0] == "GAME_OVER":
            #All players are dead, game over man. Game over.
            pass
        elif data[0] == "DISCON":
            #Our server initiated the disconnection, so lets close up shop.
            self.quit_thread()
        elif data[0] == "":
            pass
    
    
    def quit_thread(self):
        try:
            self.main_socket.send("DISCON")
        except:
            pass
        try:
            self.main_socket.close()
        except:
            pass

class ServerMode(threading.Thread):
    def __init__(self, renderman_instance, quit_socket, server_ip, server_port):
        self.renderman_instance = renderman_instance
        super(ServerMode, self).__init__()
        print "SERVER MODE INIT - nothing really happening tho. Settings:"
        print server_ip
        print server_port

class ServerClientConnection(threading.Thread):
    def __init__(self):
        super(ClientMode, self).__init__()

#Just a simple class to manage the client or server modes. Makes managing the connection from the main thread less dependent on the exact mode
class MasterNetworkMode(object):
    #Mode_data should be a dictionary where each key is a variable name for the associated mode.
    def __init__(self, renderman_instance, mode_data):
        #Again, using sockets to communicate between threads here because the
        #windows select() function can only handle sockets. Lame brah.
        self.quit_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.quit_socket.bind(("127.0.0.1", 0))
        self.shutdown_port = self.quit_socket.getsockname()[1] #Need the port number to call back later
        self.renderman_instance = renderman_instance
        self.thread_instance = None
        self.netmode = mode_data["net_mode"]
        self.mode_data = mode_data
        
        
    def startNetwork(self):
        if self.thread_instance is None:
            if self.netmode == "ClientMode":
                self.thread_instance = ClientMode(self.renderman_instance, self.quit_socket, self.mode_data["ip"], self.mode_data["port"])
            elif self.netmode == "ServerMode":
                self.thread_instance = ServerMode(self.renderman_instance, self.quit_socket, self.mode_data["ip"], self.mode_data["port"])
            self.thread_instance.start()
        else:
            print "Networking thread is already running."
    
    def stopNetwork(self):
        if self.thread_instance is not None:
            shutdown_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                shutdown_socket_sender.connect(("127.0.0.1", self.shutdown_port))
                shutdown_socket_sender.close()
            except:
                pass
        else:
            print "Networking thread is not currently running."
    
    