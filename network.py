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




#These will be moved to the settings file later
#Number of players in the game
MAX_PLAYERS = 2
#Number of seconds to wait after all players have joined before the game begins
GAME_START_WAIT = 10

WINDOW_SIZE = (500,500)
GRID_SIDE_SIZE_PX = 25
TICKRATE_MS = 200
MATH_PRECISION = 5

rows = (WINDOW_SIZE[0]/GRID_SIDE_SIZE_PX)-1
cols = (WINDOW_SIZE[1]/GRID_SIDE_SIZE_PX)-1

#Spawn point data
SPAWN_POINTS = []
SPAWN_POINTS.append([(0,0), "right"])          # Top left
SPAWN_POINTS.append([(rows, cols), "left"])    # Bottom right
SPAWN_POINTS.append([(0, cols), "right"])      # Bottom left
SPAWN_POINTS.append([(rows ,0), "left"])       # top right
SPAWN_POINTS.append([(0, cols/2), "right"])    # Middle left
SPAWN_POINTS.append([(rows, cols/2), "left"])  # Middle right
SPAWN_POINTS.append([(rows/2, 0), "right"])    # Middle Top
SPAWN_POINTS.append([(rows/2, cols), "right"]) # Middle Bottom

#Was planning on using queues to communicate between threads but the
#windows select() function can only handle sockets. Lame brah.
class ClientMode(threading.Thread):
    def __init__(self, server_ip, server_port):
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
        #print "\n%s - %s:RECEIVED VALID COMMAND: %s" % (time.time(), self.name, data[0])
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
        elif data[0] == "SERVER_MESSAGE":
            print "SERVER_MESSAGE: %s" % data[1]
        
        elif data[0] == "GAME_MODE_DATA":
            print "GOT GAME MODE DATA"
            print data[1]
            #Here we get data on screen size, grid size, and tickrate. We use this data to start up our GL game.
        
        #Unique player data. Spawn point and start direction.
        elif data[0] == "INIT_PLAYER_DATA":
            print "GOT INIT PLAYER DATA:"
            print data[1]
        
        elif data[0] == "DISCON":
            #Our server initiated the disconnection, so lets close up shop.
            self.quit_thread()
        
        elif data[0] == "TEST":
            print "GOT TEST COMMAND, REPLYING..."
            #Send back reply
            self.send_reply("%s - CLIENT ID %s REPORTING IN" % (time.time(), self.name))
        
        elif data[0] == "":
            pass
    
    def send_reply(self, reply_data):
        p_reply_data = cPickle.dumps(reply_data)
        self.main_socket.send(p_reply_data)
    
    
    def network_cleanup(self):
        #make sure everything has shut down
        try:
            self.main_socket.close()
        except:
            pass
        try:
            self.quit_socket.close()
        except:
            pass
    
    def quit_thread(self):
        print "\nQUIT CALLED"
        try:
            self.main_socket.send("DISCON")
        except:
            pass
        
        self.network_cleanup()


class SnakePlayer(object):
    def __init__(self, connection_id, start_grid, start_direction):
        self.id = connection_id
        self.alive = False
        self.current_grid = start_grid
        self.direction = start_direction

class GameServer(object):
    def __init__(self, players=[]):
        #Should be a list of SnakePlayer objects
        self.players = players
        
    #Returns a list of players and their current positions/direction
    #This data can be directly sent to clients accompanying the GAME_UPDATE command
    def get_game_update(self):
        #We should only send back new data. If the update we got from the client is the same data
        #we got the last update, dont send it out.
        pass


class ServerMode(threading.Thread):
    def __init__(self, server_ip, server_port):
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
        print "IP: %s" % server_ip
        print "Port: %s" % server_port
        print "Quit_Port: %s" % self.quit_port
        
    
    def stop_client_threads(self):
        while len(self.connections) > 0:
            #Really dont want to be modifying a list while looping over it
            thread_idx_to_pop = []
            current_connections = self.connections.keys()
            for index in current_connections:
                self.connections[index].quit_thread()
                thread_idx_to_pop.append(index)
            if len(thread_idx_to_pop) > 0:
                for i in thread_idx_to_pop:
                    del(self.connections[i])
        
            
    def close_connection_callback(self, connection_id):
        #Try to join the thread
        #THIS ISNT WORKING
        #self.connections[connection_id].join()
        #del(self.connections[connection_id])
        print "Connection %s closed" % connection_id
    
    
    def send_command(self, command, client_idx, recv=False):
        command = cPickle.dumps(command)
        if self.connections[client_idx] is not None:
            self.connections[client_idx].send_command(command, recv)
        else:
            del(self.connections[client_idx])
    
    def broadcast_command(self, command, recv=False):
        command = cPickle.dumps(command)
        current_clients = self.connections.keys()
        for client_idx in current_clients:
            if self.connections[client_idx] is not None:
                self.connections[client_idx].send_command(command, recv)
            else:
                del(self.connections[client_idx])
    
    
    #And this is where everything gets really damn complicated Im sure
    def start_game(self):
        #Lets send our clients the game-mode data before anything else
        game_mode_data = [WINDOW_SIZE, GRID_SIDE_SIZE_PX, TICKRATE_MS, MATH_PRECISION]
        self.broadcast_command(["GAME_MODE_DATA", game_mode_data])
        
        players = []
        for index, connection_id in enumerate(self.connections.keys()):
            new_player = SnakePlayer(connection_id, SPAWN_POINTS[index][0], SPAWN_POINTS[index][1])
            players.append(new_player)
            #Tell the player their spawn point
            init_player_data_command = ["INIT_PLAYER_DATA", (SPAWN_POINTS[index][0], SPAWN_POINTS[index][1])]
            self.send_command(init_player_data_command, connection_id)
        
        gameserver = GameServer(players)
        
        #Lets just send everyone a hello and tell them to get lost
        game_over = False
        game_init_start = True
        countdown = GAME_START_WAIT
        while self.quitting is False and game_over is False:
            #Initial countdown
            if game_init_start is True:
                print "STARTING GAME IN %s SECONDS..." % countdown
                if countdown == 0:
                    #GET IT ON!
                    game_init_start = False
                    #Make them all alive
                    for p in gameserver.players:
                        p.alive = True
                    self.broadcast_command(["SERVER_MESSAGE", "GAME STARTING!"])
                else:
                    #print "BCAST"
                    self.broadcast_command(["SERVER_MESSAGE", "GAME STARTING IN %s SECONDS..." % countdown])
                    countdown -= 1
                time.sleep(1)
                    
            
            #Now we're actually playing the game
            else:
                print "Sending test command..."
                self.broadcast_command(["TEST"], recv=True)
                time.sleep(1)
                
        self.quitting = True
        return True
        
    def check_connections(self):
        #Periodically check the status of our connection threads and deal with any dropped clients
        #Will probably just set their SnakePlayer.alive to False and let the clients handle it.
        pass
    
    def get_connection(self):  
        print "Waiting for players... Currently %s/%s" % (len(self.connections), MAX_PLAYERS)
        print "-----------------"
        readable, _, _ = select.select([self.main_socket, self.quit_socket], [], [], 60)
        for sock in readable:
            if sock == self.main_socket:
                connection, addy = sock.accept()
                connection.setblocking(1)
                #Create new thread to handle connection
                new_connection = ServerClientConnection(connection, self.close_connection_callback, self.nextidx)
                #Add our connection_thread to our connection tracker
                self.connections[self.nextidx] = new_connection
                self.nextidx += 1
            elif sock == self.quit_socket:
                self.quit_socket.accept()
                self.quit_socket.close()
                self.quitting = True
                return True
            continue
    
    def network_cleanup(self):
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
            print "All players are connected! Starting game in %s seconds..." % GAME_START_WAIT
            self.start_game()
        
        self.network_cleanup()
    

class ServerClientConnection(object):
    def __init__(self, client_socket, close_connection_callback, connection_id):
        self.client_socket = client_socket
        self.close_connection_callback = close_connection_callback
        self.connection_id = connection_id
        self.quitting = False
        #super(ServerClientConnection, self).__init__()
        
    def quit_thread(self):
        self.quitting = True
        self.client_socket.close()
        self.close_connection_callback(self.connection_id)
        
    def send_command(self, command, recv=False):
        try:
            #Depending on the command, we may want to wait for data as well
            self.client_socket.send(command)
            if recv is True:
                d = self.receive_data()
                if d is not None:
                    d = cPickle.loads(d)
                    print "SCC_DBG %s RETURN DATA: %s" % (self.connection_id, str(d))
                else:
                    print "SCC_DBG: Didnt get expected return data. Ruh Roh."
        except Exception as e:
            print "\nSCC_DEBUG: Something went terribly wrong here, Exception was:"
            print e
    
    def receive_data(self):
        data = None
        try:
            readable, _, _ = select.select([self.client_socket], [], [], 1) #Very low timeout, we should get data right away
            for sock in readable:
                data = sock.recv(4096)
                if data is not None and len(data) > 0:
                    return data
                elif len(data) == 0:
                    print "SCC_DBG: Connection error, quitting..."
                    self.quit_thread()
                else:
                    return None
        except:
            self.quit_thread()
        


#Just a simple class to manage the client or server modes. Makes managing the connection from the main thread less dependent on the exact mode
class MasterNetworkMode(object):
    #Mode_data should be a dictionary where each key is a variable name for the associated mode.
    def __init__(self, mode_data):
        self.netmode = mode_data["net_mode"]
        self.mode_data = mode_data
        self.client_thread = None
        self.server_thread = None
        
    
    
    #The idea here is that regardless of whether we are running ClientMode or ServerMode, we are always running a game instance as well
    #Even in ServerMode, however, we still run a ClientMode connected locally to the ServerMode.
    def game_tick(self):
        #print "TICK TOCK MOTHERFUCKER"
        
        pass
    
    
    def startNetwork(self):
        #Should we run a server?
        if self.netmode == "ServerMode":
            if self.server_thread is None:
                self.server_thread = ServerMode(self.mode_data["ip"], self.mode_data["port"])
                self.server_thread.start()
                #Modify our IP if we are running a server so our client thread connects correctly
                self.mode_data["ip"] = "127.0.0.1"
        
        if self.client_thread is None:
                self.client_thread = ClientMode(self.mode_data["ip"], self.mode_data["port"])
                self.client_thread.start()
        
    
    def stopNetwork(self):
        close_network_helper(self.client_thread)
        if self.netmode == "ServerMode":
            close_network_helper(self.server_thread)
    

def close_network_helper(network_thread):
    if network_thread is not None:
        if network_thread.is_alive() is True:
            shutdown_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                shutdown_socket_sender.connect(("127.0.0.1", network_thread.quit_port))
                shutdown_socket_sender.close()
            except:
                pass
        else:
            #This was probably already run once but we need to make sure
            #Its possible the thread died and never cleaned itself up
            network_thread.network_cleanup()
            network_thread.join()
            network_thread = None
    else:
        print "%s: Networking thread is not currently running." % repr(network_thread)

