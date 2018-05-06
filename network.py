import socket
import select
import threading
import time
import cPickle
import Queue
from sys import exit as sys_exit

#None of our exit methods work from inside here because of the way
#the GLUT mainloop works. Lets redefine sys_exit to be a callback
#into the GLUT loop so we can kill it from there.

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




#This will be moved to the settings file later
MAX_PLAYERS = 3

#Was planning on using queues to communicate between threads but the
#windows select() function can only handle sockets. Lame brah.
class ClientMode(threading.Thread):
    def __init__(self, renderman_instance, server_ip, server_port):
        self.renderman_instance = renderman_instance
        self.server_ip = server_ip
        self.server_port = int(server_port)
        self.quit_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.quit_socket.bind(("127.0.0.1", 0))
        self.quit_port = self.quit_socket.getsockname()[1]
        self.main_socket = None
        self.quitting = False
        super(ClientMode, self).__init__()
        
    #Main part of our thread
    def run(self):
        self.quit_socket.listen(1)
        #Try and initialize a connection with our server. If we can't its already over.
        #Using streaming TCP sockets. UDP is overkill for what we are doing.
        self.main_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.main_socket.setblocking(1)
        try:
            self.main_socket.connect((self.server_ip, self.server_port))
            print "Connected to game server. Waiting for data..."
        except:
            print "Problem connecting to the server. Check the IP/port in your config. Quitting..."
            sys_exit()
        
        #Ok we have a good connection to the server. Lets listen for any data
        while self.quitting == False:
            data = None
            try:
                readable, _, _ = select.select([self.main_socket, self.quit_socket], [], [], 60) #60 second timeout
                for sock in readable:
                    if sock == self.main_socket:
                        data = self.main_socket.recv(8192)
                        #Handle any commands we get
                        if len(data) == 0:
                            self.quit_thread()
                        elif data is not None and len(data) > 0:
                            self.process_command(data)
                        continue
                    elif sock == self.quit_socket:
                        self.quit_socket.accept()
                        self.quit_socket.close()
                        self.quitting = True
                        break
            except Exception as e:
                print "CM DEBUG: %s" % str(e)
                break
        #Got the message to quit or the thread died, either way lets quit
        self.quit_thread()
    
    
    def process_command(self, rawdata):
        try:
            data = cPickle.loads(rawdata)
            if isinstance(data, list) is False:
                print "Pickled data was not a list, something is horribly wrong here so im quiting..."
                #sys_exit()
                return
        except:
            #Major error, blow up
            print "\nCommand processing error, couldn't load pickel data."
            #sys_exit()
            return
        print "\n%s - %s:RECEIVED VALID COMMAND: %s" % (time.time(), self.name, data[0])
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
        print "\nQUIT CALLED"
        try:
            self.main_socket.send("DISCON")
        except:
            pass
        try:
            self.main_socket.close()
        except:
            pass

class ServerMode(threading.Thread):
    def __init__(self, renderman_instance, server_ip, server_port):
        self.renderman_instance = renderman_instance
        self.quit_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.quit_socket.bind(("127.0.0.1", 0))
        self.quit_port = self.quit_socket.getsockname()[1]
        self.connections = {}
        self.nextidx = 0
        self.server_ip = server_ip
        self.quitting = False
        if isinstance(server_port, basestring):
            try:
                self.server_port = int(server_port)
            #Something messed up with the supplied port, we go automode
            except:
                self.server_port = 0
        elif isinstance(server_port, int):
            self.server_port = server_port
            
        super(ServerMode, self).__init__()
        print "SERVER MODE INIT - Settings:"
        print server_ip
        print server_port
        print self.quit_port
        
    
    def stop_client_threads(self):
        while len(self.connections) > 0:
            #Really dont want to be modifying a list while looping over it
            thread_idx_to_pop = []
            current_connections = self.connections.keys()
            for index in current_connections:
                cli_thread = self.connections[index]
                if cli_thread.is_alive() is False:
                    cli_thread.join()
                    thread_idx_to_pop.append(index)
                else:
                    cli_thread.quit_thread()
            if len(thread_idx_to_pop) > 0:
                for i in thread_idx_to_pop:
                    del(self.connections[i])
        
            
    def close_connection_callback(self, connection_id):
        #Try to join the thread
        #THIS ISNT WORKING
        #self.connections[connection_id].join()
        #del(self.connections[connection_id])
        pass
    
    
    def send_command(self, command, client_idx):
        command = cPickle.dumps(command)
        if self.connections[client_idx].is_alive() is True:
            self.connections[client_idx].send_command(command)
        else:
            del(self.connections[client_idx])
    
    def broadcast_command(self, command):
        command = cPickle.dumps(command)
        current_clients = self.connections.keys()
        for client_idx in current_clients:
            if self.connections[client_idx].is_alive() is True:
                self.connections[client_idx].send_command(command)
            else:
                del(self.connections[client_idx])
    
    
    #And this is where everything gets really damn complicated Im sure
    def start_game(self):
        #Lets just send everyone a hello and tell them to get lost
        while self.quitting is False:
            self.broadcast_command(["GET_NEXT_MOVE"])
            time.sleep(1)
        self.quitting = True
        return True
        
    
    
    def get_connection(self):  
        print "Waiting for players... Currently %s/%s" % (len(self.connections), MAX_PLAYERS)
        print "-----------------"
        readable, _, _ = select.select([self.main_socket, self.quit_socket], [], [], 60)
        for sock in readable:
            if sock == self.main_socket:
                connection, addy = sock.accept()
                connection.setblocking(1)
                #Create new thread to handle connection
                connection_thread = ServerClientConnection(connection, self.close_connection_callback, self.nextidx)
                connection_thread.start()
                #Add our connection_thread to our connection tracker
                self.connections[self.nextidx] = connection_thread
                self.nextidx += 1
            elif sock == self.quit_socket:
                self.quit_socket.accept()
                self.quit_socket.close()
                self.quitting = True
                return True
            continue
    
    def run(self):
        self.quit_socket.listen(1)
        #Set up our listening socket
        self.main_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            self.main_socket.bind((self.server_ip, self.server_port))
            #Update our port number incase we automatically got a port (port=0)
            self.server_port = self.main_socket.getsockname()[1]
            self.main_socket.setblocking(1)
            self.main_socket.listen(1)
        except:
            return
        
        print "PyGLSnake Multiplayer Server running!"
        print "Listening for player at ip: %s  on port %s..." % (self.server_ip, self.server_port)
        
        #This should halt run() until we get the quit signal 
        while self.quitting is False and len(self.connections) < MAX_PLAYERS:
            self.get_connection()
        if self.quitting is False:
            print "All players are connected! Starting game in %s seconds..." % 10 # REPLACEME LATER WITH VAR
            self.start_game()
        
        #make sure everything has shut down
        self.stop_client_threads()
        try:
            self.main_socket.close()
        except:
            pass
        try:
            self.quit_socket.close()
        except:
            pass
        
        return
        
    

class ServerClientConnection(threading.Thread):
    def __init__(self, client_socket, close_connection_callback, connection_id):
        self.client_socket = client_socket
        self.close_connection_callback = close_connection_callback
        self.connection_id = connection_id
        self.quitting = False
        super(ServerClientConnection, self).__init__()
        
    def quit_thread(self):
        self.quitting = True
        self.client_socket.close()
        self.close_connection_callback(self.connection_id)
        
    def send_command(self, command):
        try:
            #Depending on the command, we may want to wait for data as well
            self.client_socket.send(command)
            if command == "":
                self.receive_data()
        except Exception as e:
            print "\nSCC_DEBUG: Something went terribly wrong here, Exception was:"
            print e
    
    def receive_data(self):
        data = None
        try:
            readable, _, _ = select.select([self.client_socket], [], [], 60)
            for sock in readable:
                data = self.sock.recv(4096)
                return data
        except:
            self.quit_thread()
        
    def run(self):
        while self.quitting is False:
            self.receive_data()


#Just a simple class to manage the client or server modes. Makes managing the connection from the main thread less dependent on the exact mode
class MasterNetworkMode(object):
    #Mode_data should be a dictionary where each key is a variable name for the associated mode.
    def __init__(self, renderman_instance, mode_data):
        self.renderman_instance = renderman_instance
        self.thread_instance = None
        self.netmode = mode_data["net_mode"]
        self.mode_data = mode_data
        
        
    def startNetwork(self):
        if self.thread_instance is None:
            if self.netmode == "ClientMode":
                self.thread_instance = ClientMode(self.renderman_instance, self.mode_data["ip"], self.mode_data["port"])
            elif self.netmode == "ServerMode":
                self.thread_instance = ServerMode(self.renderman_instance, self.mode_data["ip"], self.mode_data["port"])
            self.thread_instance.start()
        else:
            print "Networking thread is already running."
    
    def stopNetwork(self):
        if self.thread_instance is not None:
            if self.thread_instance.is_alive() is True:
                shutdown_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    shutdown_socket_sender.connect(("127.0.0.1", self.thread_instance.quit_port))
                    shutdown_socket_sender.close()
                except:
                    pass
            else:
                self.thread_instance = None
        else:
            print "Networking thread is not currently running."
    
    