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
        self.is_connected = False
        self.quitting = False
        self.game_mode_params = None
        self.init_player_data = None
        self.snake_reference = None
        self.connection_id = "NOT_CONNECTED"
        super(ClientMode, self).__init__()
        
    #Main part of our thread
    def run(self):
        self.quit_socket.listen(1)
        #Try and initialize a connection with our server. If we can't its already over.
        #Using streaming TCP sockets.
        #Because we're using a speak-when-spoken-to communication style with our client and servers,
        #it may actually be worth it to just use UDP instead here.
        #Unfortunately I'm not well versed in using UDP sockets so prolly not.
        
        self.main_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.main_socket.setblocking(1)
        try:
            self.main_socket.connect((self.server_ip, self.server_port))
            print "Connected to game server. Waiting for data..."
        except:
            print "Problem connecting to the server. Check the IP/port in your config. Quitting..."
            return
        self.is_connected = True
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
            self.game_mode_params = data[1]
            #Here we get data on screen size, grid size, and tickrate. We use this data to start up our GL game.
        
        #Unique player data. Spawn point and start direction.
        elif data[0] == "INIT_PLAYER_DATA":
            print "GOT INIT PLAYER DATA: % "
            self.init_player_data = data[1]
            self.init_player_data["init_snake_size"] = self.game_mode_params["INIT_SNAKE_SIZE"]
            self.connection_id = self.init_player_data["connection_id"]
        
        elif data[0] == "DISCON":
            #Our server initiated the disconnection, so lets close up shop.
            self.quit_thread()
        
        elif data[0] == "TEST":
            print "GOT TEST COMMAND, REPLYING..."
            #Send back reply
            self.send_reply("%s - CLIENT ID %s REPORTING IN" % (time.time(), self.connection_id))
        
        elif data[0] == "":
            pass
    
    def send_reply(self, reply_data):
        p_reply_data = cPickle.dumps(reply_data)
        self.main_socket.send(p_reply_data)
    
    
    def getInitPlayerData(self):
        while self.init_player_data is None:
            time.sleep(0.25) #I dont like using sleep here, theres probably a better way to do this with callbacks.
        return self.init_player_data
    
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
    def __init__(self, server_mode_ctx, players={}):
        self.server_mode_ctx = server_mode_ctx
        #Should be a list of SnakePlayer objects
        self.players = players
        
    #Returns a list of players and their current positions/direction
    #This data can be directly sent to clients accompanying the GAME_UPDATE command
    def get_game_update(self):
        #We should only send back new data. If the update we got from the client is the same data
        #we got the last update, dont send it out.
        pass
    
    
    #This function assumes state_data contains all data required.
    def set_player_state(self, connection_id, state_data):
        self.players[connection_id].alive = state_data["alive"]
        self.players[connection_id].current_grid = state_data["current_grid"]
        self.players[connection_id].direction = state_data["direction"]
    
    
    #We do things oddly here just to allow for updating only one item at a time if necessary
    #i.e. just update the alive state without resetting position or direction
    def update_player_state(self, connection_id, state_data):
        #Only 3 possible values we can mess with, alive, current_grid, and direction.
        if state_data.has_key("alive") is True:
            self.players[connection_id].alive = state_data["alive"]
            
        if state_data.has_key("current_grid") is True and len(state_data["current_grid"]) > 0:
            self.players[connection_id].current_grid = state_data["current_grid"]
            
        if state_data.has_key("direction") is True and len(state_data["direction"]) > 0:
            self.players[connection_id].direction = state_data["direction"]
            
    def get_player_state(self, connection_id):
        return_state_data = {}
        return_state_data["alive"] = self.players[connection_id].alive
        return_state_data["current_grid"] = self.players[connection_id].current_grid
        return_state_data["direction"] = self.players[connection_id].direction
        return return_state_data
        

class ServerMode(threading.Thread):
    def __init__(self, server_ip, server_port, game_mode_params):
        self.quit_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.quit_socket.bind(("127.0.0.1", 0))
        self.quit_port = self.quit_socket.getsockname()[1]
        self.connections = {}
        self.nextidx = 0
        self.server_ip = server_ip
        self.quitting = False
        self.game_mode_params = game_mode_params
        self.gameserver = None
        #Eh might as well do this here
        rows = (self.game_mode_params["WINDOW_SIZE"][0]/self.game_mode_params["GRID_SIDE_SIZE_PX"])-1
        cols = (self.game_mode_params["WINDOW_SIZE"][1]/self.game_mode_params["GRID_SIDE_SIZE_PX"])-1
        self.SPAWN_POINTS = []
        self.SPAWN_POINTS.append([(0,0), "right"])          # Top left
        self.SPAWN_POINTS.append([(rows, cols), "left"])    # Bottom right
        self.SPAWN_POINTS.append([(0, cols), "right"])      # Bottom left
        self.SPAWN_POINTS.append([(rows ,0), "left"])       # top right
        self.SPAWN_POINTS.append([(0, cols/2), "right"])    # Middle left
        self.SPAWN_POINTS.append([(rows, cols/2), "left"])  # Middle right
        self.SPAWN_POINTS.append([(rows/2, 0), "right"])    # Middle Top
        self.SPAWN_POINTS.append([(rows/2, cols), "right"]) # Middle Bottom
        
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
        print "Game mode params:"
        print self.game_mode_params
        
    
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
        print "Connection %s closed" % connection_id
        self.connections[connection_id] = None
        del(self.connections[connection_id])
        #Connection closed, set the associated player to being Dead
        self.gameserver.update_player_state(connection_id, {"alive": False})
    
    
    def data_update_callback(self, connection_id, recv_data):
        print "GOT RECV DATA FROM CONNECTION ID: %s" % connection_id
        print "DATA: "
        print recv_data
    
    
    def send_command(self, command, client_idx, recv=False):
        command = cPickle.dumps(command)
        if self.connections[client_idx] is not None:
            self.connections[client_idx].send_command(command, recv)
    
    def broadcast_command(self, command, recv=False):
        command = cPickle.dumps(command)
        current_clients = self.connections.keys()
        for client_idx in current_clients:
            if self.connections[client_idx] is not None:
                self.connections[client_idx].send_command(command, recv)
    
    #And this is where everything gets really damn complicated Im sure
    def start_game(self):
        #Lets send our clients the game-mode data before anything else
        self.broadcast_command(["GAME_MODE_DATA", self.game_mode_params])
        
        
        #Set up the individual SnakePlayer objects for each of our connections
        #Then pass that over to our GameServer object
        #During the setup of each player we send out player-specific data to the client
        players = {}
        for index, connection_id in enumerate(self.connections.keys()):
            new_player = SnakePlayer(connection_id, self.SPAWN_POINTS[index][0], self.SPAWN_POINTS[index][1])
            players[connection_id] = new_player
            #Tell the player their spawn point
            init_player_data = {}
            init_player_data["start_grid"] = self.SPAWN_POINTS[index][0]
            init_player_data["direction"] = self.SPAWN_POINTS[index][1]
            init_player_data["connection_id"] = connection_id
            init_player_data_command = ["INIT_PLAYER_DATA", init_player_data]
            self.send_command(init_player_data_command, connection_id)
        
        self.gameserver = GameServer(self, players)
        
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
                    for _, p in self.gameserver.players.iteritems():
                        p.alive = True
                    self.broadcast_command(["SERVER_MESSAGE", "GAME STARTING!"])
                else:
                    #print "BCAST"
                    self.broadcast_command(["SERVER_MESSAGE", "GAME STARTING IN %s SECONDS..." % countdown])
                    countdown -= 1
                time.sleep(1)
                    
            
            #Now we're actually playing the game
            else:
                #Prune connections, if all clients have disconnected its game over
                self.check_connections()
                if len(self.connections) == 0:
                    print "All players disconnected, game over man!"
                    game_over = True
                    continue
                
                
                print "Sending test command..."
                self.broadcast_command(["TEST"], recv=True)
                time.sleep(1)
                
        self.quitting = True
        return True
        
    def check_connections(self):
        bad_cons = []
        for connection_id, connection in self.connections.iteritems():
            if connection.quitting is True:
                bad_cons.append(connection_id)
        for connection_id in bad_cons:
            del(self.connections[connection_id])
            self.gameserver.update_player_state(connection_id, {"alive": False})
    
    def get_connection(self):  
        print "Waiting for players... Currently %s/%s" % (len(self.connections), MAX_PLAYERS)
        print "-----------------"
        readable, _, _ = select.select([self.main_socket, self.quit_socket], [], [], 60)
        for sock in readable:
            if sock == self.main_socket:
                connection, addy = sock.accept()
                connection.setblocking(1)
                #Create new thread to handle connection
                new_connection = ServerClientConnection(connection, self.close_connection_callback, self.data_update_callback, self.nextidx)
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
    def __init__(self, client_socket, close_connection_callback, data_update_callback, connection_id):
        self.client_socket = client_socket
        self.close_connection_callback = close_connection_callback
        self.data_update_callback = data_update_callback
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
                    #Tell the main thread we got some data for it
                    self.data_update_callback(self.connection_id, d)
                else:
                    print "SCC_DBG: Didnt get expected return data. Ruh Roh."
        except Exception as e:
            if e.args[0] in [10053, 10054, 9]:
                print "\n[%s] SCC_DEBUG: Client connection closed, we're done." % self.connection_id
                self.quit_thread()
            else:
                print "\n[%s] SCC_DEBUG: Something went terribly wrong here, Exception was:" % self.connection_id
                print e.args
            
    
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
        #Game params will be None if run in ClientMode
        self.game_params = mode_data["game_params"]
        self.ip = mode_data["ip"]
        self.port = mode_data["port"]
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
                self.server_thread = ServerMode(self.ip, self.port, self.game_params)
                self.server_thread.start()
                #Modify our IP if we are running a server so our client thread connects correctly
                self.ip = "127.0.0.1"
        
        if self.client_thread is None:
                self.client_thread = ClientMode(self.ip, self.port)
                self.client_thread.start()
        
    
    def stopNetwork(self):
        close_network_helper(self.client_thread)
        if self.netmode == "ServerMode":
            close_network_helper(self.server_thread)
            
    def getParameters(self):
        if self.netmode == "ServerMode":
            return self.game_params
        elif self.netmode == "ClientMode":
            while self.client_thread.is_connected is False and self.client_thread.isAlive() is True:
                #Just lie in wait...
                time.sleep(1)
            if self.client_thread.is_connected is True:
                #Now wait for the client thread to receive game params, this should be pretty quick
                while self.client_thread.game_mode_params is None:
                    #Oh just a matter of time now....
                    #Um yeah this could repeat forever, so yeah.... Maybe not do that?
                    time.sleep(0.25)
                
                return self.client_thread.game_mode_params
            else:
                return None
    
    def setSnakeReference(self, snake_reference):
        self.client_thread.snake_reference = snake_reference
    

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
        print "%s: Networking thread is not currently running." % network_thread.name

