import socket
import select
import threading
import time
import cPickle
from copy import deepcopy
from random import randint
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
GAME_START_WAIT = 5
#Maximum number of objectives on the grid at once
MAX_OBJECTIVES = 7

OBJ_TICK = 20

#Your color corresponds to your connection_id
# UPDATE CLIENT CODE TO USE ITS OWN CONNECTION_ID INSTEAD OF RELYING ON INIT_PLAYER_DATA!
SNAKE_COLORS = []
SNAKE_COLORS.append([(255, 0, 0), (167, 0, 0)])
SNAKE_COLORS.append([(255, 110, 40), (205, 67, 0)])
SNAKE_COLORS.append([(0, 255, 191), (0, 179, 134)])
SNAKE_COLORS.append([(0, 140, 255), (0, 87, 158)])
SNAKE_COLORS.append([(255, 208, 0), (161, 131, 0)])
SNAKE_COLORS.append([(119, 0, 255), (65, 0, 140)])
SNAKE_COLORS.append([(255, 0, 255), (165, 0, 165)])
SNAKE_COLORS.append([(224, 117, 210), (140, 111, 131)])

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
        self.grid_reference = None
        self.connection_id = None
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
            #try: #Some of these try/except statements, while a good idea, are making it difficult to debug errors.
                readable, _, _ = select.select([self.main_socket, self.quit_socket], [], [], 60) #60 second timeout
                for sock in readable:
                    if sock == self.main_socket:
                        data = self.main_socket.recv(8192)
                        #Handle any commands we get
                        if len(data) == 0:
                            self.quitThread()
                        elif data is not None and len(data) > 0:
                            self.processCommand(data)
                        continue
                    elif sock == self.quit_socket:
                        self.quit_socket.accept()
                        self.quit_socket.close()
                        self.quitting = True
                        break
            #except:
            #    self.quitting = True
            #    break
            
        #Got the message to quit or the thread died, either way lets quit
        self.quitThread()
    
    
    def processCommand(self, rawdata):
        try:
            data = cPickle.loads(rawdata)
            if isinstance(data, list) is False:
                print "Pickled data was not a list, something is horribly wrong here so im quiting..."
                #sys_exit()
                return
        except:
            #Major error, blow up
            print "\nCommand processing error, couldn't load pickle data."
            #sys_exit()
            return
        #print "\n%s - %s:RECEIVED VALID COMMAND: %s" % (time.time(), self.name, data[0])
        
        if data[0] == "GET_NEXT_MOVE":
            #Only update if we are still alive
            netupd = self.snake_reference.getOurSnakeData()
            if netupd["alive"] is True:
                self.sendReply("PLAYER_DATA_UPDATE", netupd)
        
        elif data[0] == "GAME_UPDATE":
            all_snake_data = data[1][0]
            objective_data = data[1][1]
            self.snake_reference.setAllSnakesData(all_snake_data)
            self.grid_reference.setObjectiveData(objective_data)
        
        elif data[0] == "YOU_DIED":
            print "WE DIED! Reason: %s" % data[1]
            self.quitThread()
        
        elif data[0] == "GAME_START":
            #Game is starting
            #Here we just switch modes or something, I dunno. Im not sure we even need this
            #Although now that I think about it the only other way would be to go by the SERVER_MESSAGE
            #So yeah this is needed, ugh.
            print "GAME ON!!!!!"
            #Send out the first update manually, this one just sets all the players to alive and nothing else
            self.snake_reference.setAllPlayersVar("alive", True)
            
        
        elif data[0] == "GAME_OVER":
            print "Got game over signal, game over man!"
            self.quitThread()
            
        elif data[0] == "SERVER_MESSAGE":
            print "SERVER_MESSAGE: %s" % data[1]
        
        elif data[0] == "GAME_MODE_DATA":
            self.game_mode_params = data[1]
        
        #our connection_id is extremely important for each client to have
        elif data[0] == "CON_ID":
            self.connection_id = data[1]
            print "GOT CONNECTION ID %s" % data[1]
        
        #Unique player data. Spawn point and start direction.
        elif data[0] == "INIT_PLAYER_DATA":
            self.init_player_data = data[1]
            #Set up the snake grid with other players here... or somewhere else I dont care
        
        elif data[0] == "DISCON":
            #Our server initiated the disconnection, so lets close up shop.
            self.quitThread()
        
        elif data[0] == "TEST":
            print "GOT TEST COMMAND, REPLYING..."
            #Send back reply
            self.sendReply("TEST_CMD", "%s - CLIENT ID %s REPORTING IN" % (time.time(), self.connection_id))
        
        elif data[0] == "":
            pass
    
    def sendReply(self, reply_type, reply_data):
        p_reply_data = cPickle.dumps([reply_type, reply_data])
        self.main_socket.send(p_reply_data)
    
    def networkCleanup(self):
        #make sure everything has shut down
        try:
            self.main_socket.close()
        except:
            pass
        try:
            self.quit_socket.close()
        except:
            pass
    
    def quitThread(self):
        print "\nQUIT CALLED"
        try:
            self.main_socket.send("DISCON")
        except:
            pass
        
        self.networkCleanup()


class SnakePlayer(object):
    def __init__(self, connection_id, start_grid, start_direction, start_length):
        self.connection_id = connection_id
        self.current_grid = start_grid
        self.direction = start_direction
        self.alive = False
        self.snake_grids = [start_grid]
        self.length = start_length

class GameServer(object):
    def __init__(self, server_mode_ctx, players={}):
        self.server_mode_ctx = server_mode_ctx
        #Should be a list of SnakePlayer objects
        self.players = players
        self.objectives = []
        self.dead_players = {}
        self.current_tick = 0
        self.cur_mode = "GET"
    
    
    #Check if a single grid is currently occupied.
    def checkSingleCollision(self, grid):
        if grid in self.objectives:
            return True
        for snakeobj in self.players.values():
            if grid in snakeobj.snake_grids:
                return True
        return False
    
    def checkForCollisions(self):
        #Check if alive first
        #Check if head of snake (next move) is in an occupied block
        #Check if that occupied block is the head of another snake
        #   -If yes and that snake has updated, set that other snake to dead too
        #Set our snake to dead
        
        #Figure out all the occupied blocks
        #Its unfortunate but we have to loop through this data twice
        #I will think about how not to do that....
        all_snake_heads = []
        all_occupied_grids = []
        for _, snakeobj in self.players.iteritems():
            all_snake_heads += snakeobj.snake_grids[-1]
            all_occupied_grids += snakeobj.snake_grids
            
        dead_players = []
        for connection_id, snakeobj in self.players.iteritems():
            if snakeobj.alive == True:
                #Check for collision with an objective block
                if snakeobj.snake_grids[-1] in self.objectives:
                    snakeobj.length += 1
                    self.objectives.remove(snakeobj.snake_grids[-1])
                    
                
                #Check for wall collision
                next_move = snakeobj.snake_grids[-1]
                if ((0 <= next_move[0] < self.server_mode_ctx.rows+1) and (0 <= next_move[1] < self.server_mode_ctx.cols+1)) is False:
                    print "PLAYER %s HIT WALL" % connection_id
                    snakeobj.alive = False
                    self.server_mode_ctx.sendCommand(["YOU_DIED", "HIT A WALL"], snakeobj.connection_id)
                    
            
            #Checking snakeobj.alive again, maybe the wall collision killed out snake
            #Check for collision with other snakes
            if snakeobj.alive == True:
                #check if this snake's head is in an already occupied grid
                #We filter out our own snake by looking at the grid before the head (the snake's neck)
                snake_head = snakeobj.snake_grids[-1]
                snake_neck = snakeobj.snake_grids[-2]
                #Get indices where our snake head is. There should be at least one, our actual location.
                #if there is another, thats another snake and we just ran into it.
                #So many loops, I really am not fond of this function already
                for index, ogrid in enumerate(all_occupied_grids):
                    if ogrid == snake_head:
                        #Make sure this isn't us
                        if all_occupied_grids[index-1] != snake_neck:
                            #Ok so we died.
                            #We would back up but we cant since we dont have information on the previous tail grid
                            #So the dead snake is actually one grid shorter than it was before it died.
                            #Just imagine the snake pancaked against the obstacle ala Wile E. Coyote :P
                            snakeobj.alive = False
                            self.server_mode_ctx.sendCommand(["YOU_DIED", "HIT ANOTHER SNAKE"], snakeobj.connection_id)
                            
                            #Remove the head since that would be intersecting the grid we collided with
                            #Special case, head on collision we will let them intersect, otherwise it looks weird (like we collided with nothing)
                            if ogrid not in all_snake_heads:
                                del(snakeobj.snake_grids[-1])
            else:
                dead_players.append(connection_id)
        
    
    #This function runs twice per client game tick
    def halfTick(self):
        #Now we're actually playing the game
        #The basic order for each game tick is as follows:
        #Broadcast command for getting new player state
        # - NOT DOING THIS YET - Compare data and separate new player information
        #Check stuffs:
        #   All players dead? Game over. That kinda stuff
        #Broadcast command for updating new player state
        
        
        
        #MAIN GAME LOOP
        #Yeah I didnt think this was a good idea either, but It does work so yeah....
        #Modes are GET and SEND, but they could have just as easily been 0 or 1. This is easier to follow.
        
        
        #Get updates from clients
        if self.cur_mode == "GET":
            get_cmd = ["GET_NEXT_MOVE"]
            self.server_mode_ctx.broadcastCommand(get_cmd, recv=True)
            
            
            #Lastly switch our mode
            self.cur_mode = "SEND"
        
        #Send updates to clients. This corresponds with the client's game tick.
        else:
            #Check for collisions before we send out updates
            self.checkForCollisions()
            #Only update objectives every OBJ_TICK'th tick
            if self.current_tick % OBJ_TICK == 0:
                self.updateObjectives()
            player_update = self.getPlayerStateAll()
            objective_update = self.objectives
            game_update = [player_update, objective_update]
            send_cmd = ["GAME_UPDATE", game_update]
            self.server_mode_ctx.broadcastCommand(send_cmd)
            
            #And of course, switch our mode back
            self.cur_mode = "GET"
            #We've officially completed a single tick, congrats
            self.current_tick += 1
    
    #This function assumes state_data contains all data required.
    def setPlayerState(self, connection_id, state_data):
        self.players[connection_id].alive = state_data["alive"]
        self.players[connection_id].current_grid = state_data["current_grid"]
        self.players[connection_id].direction = state_data["direction"]
        self.players[connection_id].snake_grids = state_data["snake_grids"]
        self.players[connection_id].length = state_data["length"]
    
    #We do things oddly here just to allow for updating only one item at a time if necessary
    #i.e. just update the alive state without resetting position or direction
    def updatePlayerState(self, connection_id, state_data):
        #Only 3 possible values we can mess with, alive, current_grid, and direction.
        if state_data.has_key("alive") is True:
            self.players[connection_id].alive = state_data["alive"]
            
        if state_data.has_key("current_grid") is True and len(state_data["current_grid"]) > 0:
            self.players[connection_id].current_grid = state_data["current_grid"]
            
        if state_data.has_key("direction") is True and len(state_data["direction"]) > 0:
            self.players[connection_id].direction = state_data["direction"]
        
        if state_data.has_key("snake_grids") is True and len(state_data["snake_grids"]) > 0:
            self.players[connection_id].snake_grids = state_data["snake_grids"]
        
        if state_data.has_key("length") is True:
            self.players[connection_id].length = state_data["length"]
            
        #Here we also check to see if there were any collisions or objectives collected
        #We then update the player's state again with this new information
        #This all gets sent back to the client later
    
    
    def getPlayerStateAll(self):
        return_state_data = {}
        #more bullcrap with dictionary changing size during iteration.
        #Happens if a player quits mid-game. This should fix it....
        connections = self.players.keys()
        for connection_id in connections:
            playerobj = self.players[connection_id]
            #We don't need to keep updating players of a dead player's status so
            #if we encounter a dead player send it out once and then remove the player
            #from self.players.
            player_data = {}
            player_data["alive"] = playerobj.alive
            player_data["current_grid"] = playerobj.current_grid
            player_data["direction"] = playerobj.direction
            player_data["snake_grids"] = playerobj.snake_grids
            player_data["length"] = playerobj.length
            return_state_data[connection_id] = player_data
            
            #Dead player
            if playerobj.alive == False:
                self.dead_players[connection_id] = deepcopy(playerobj) #Copying because I think we would delete both below otherwise. References brah.
                del(self.players[connection_id])
            
        return return_state_data
    
    def updateObjectives(self):
        if len(self.objectives) == MAX_OBJECTIVES:
            self.objectives.pop(0)
        
        #Generate a random grid number and make sure its not currently occupied
        obj_grid = (randint(0, self.server_mode_ctx.rows-1), randint(0, self.server_mode_ctx.cols-1))
        while self.checkSingleCollision(obj_grid) is True:
            obj_grid = (randint(0, self.server_mode_ctx.rows-1), randint(0, self.server_mode_ctx.cols-1))
        self.objectives.append(obj_grid)
        

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
        self.rows = (self.game_mode_params["WINDOW_SIZE"][0]/self.game_mode_params["GRID_SIDE_SIZE_PX"])-1
        self.cols = (self.game_mode_params["WINDOW_SIZE"][1]/self.game_mode_params["GRID_SIDE_SIZE_PX"])-1
        self.SPAWN_POINTS = []
        self.SPAWN_POINTS.append([(0,0), "right"])          # Top left
        self.SPAWN_POINTS.append([(self.rows, self.cols), "left"])    # Bottom right
        self.SPAWN_POINTS.append([(0, self.cols), "right"])      # Bottom left
        self.SPAWN_POINTS.append([(self.rows ,0), "left"])       # top right
        self.SPAWN_POINTS.append([(0, self.cols/2), "right"])    # Middle left
        self.SPAWN_POINTS.append([(self.rows, self.cols/2), "left"])  # Middle right
        self.SPAWN_POINTS.append([(self.rows/2, 0), "right"])    # Middle Top
        self.SPAWN_POINTS.append([(self.rows/2, self.cols), "right"]) # Middle Bottom
        
        if isinstance(server_port, basestring):
            try:
                self.server_port = int(server_port)
            #Something messed up with the supplied port, we go automode
            except:
                self.server_port = 0
        elif isinstance(server_port, int):
            self.server_port = server_port
        else:
            #Something REALLY messed up here, automode to the rescue!
            self.server_port = 0
            
        super(ServerMode, self).__init__()
        print "SERVER MODE INIT - Settings:"
        print "IP: %s" % server_ip
        print "Port: %s" % server_port
        print "Quit_Port: %s" % self.quit_port
        print "Game mode params:"
        print self.game_mode_params
        
    
    def stopClientThreads(self):
        while len(self.connections) > 0:
            #Really dont want to be modifying a list while looping over it
            thread_idx_to_pop = []
            current_connections = self.connections.keys()
            for index in current_connections:
                self.connections[index].quitThread()
                thread_idx_to_pop.append(index)
            if len(thread_idx_to_pop) > 0:
                for i in thread_idx_to_pop:
                    del(self.connections[i])
        
            
    def closeConnectionCallback(self, connection_id):
        print "Connection %s closed" % connection_id
        self.connections[connection_id] = None
        del(self.connections[connection_id])
        #Connection closed, set the associated player to being Dead
        try:
            self.gameserver.updatePlayerState(connection_id, {"alive": False})
        except:
            #Maybe the client was killed by the server, in which case it is already set to not alive
            pass
    
    
    def dataUpdateCallback(self, connection_id, recv_data):
        if recv_data[0] == "PLAYER_DATA_UPDATE":
            self.gameserver.setPlayerState(recv_data[1]["connection_id"], recv_data[1])
        
        elif recv_data[0] == "":
            pass
        elif recv_data[0] == "":
            pass
        
        #if recv_data[0] == "TEST_CMD":
        #    print "GOT TEST COMMAND FROM CONNECTION ID: %s" % connection_id
        
        
    
    
    def sendCommand(self, command, client_idx, recv=False):
        command = cPickle.dumps(command)
        if self.connections[client_idx] is not None:
            self.connections[client_idx].sendCommand(command, recv)
    
    def broadcastCommand(self, command, recv=False):
        command = cPickle.dumps(command)
        current_clients = self.connections.keys()
        for client_idx in current_clients:
            if self.connections[client_idx] is not None:
                self.connections[client_idx].sendCommand(command, recv)
    
    #And this is where everything gets really damn complicated Im sure
    def startGame(self):
        #Sleeping because something weird is going on and sometimes this command never gets to the clients
        time.sleep(0.1)
        #Lets send our clients the game-mode data before anything else
        self.broadcastCommand(["GAME_MODE_DATA", self.game_mode_params])
        
        
        #Set up the individual SnakePlayer objects for each of our connections
        #Then pass that over to our GameServer object
        init_player_data_all = {}
        players = {}
        for index, connection_id in enumerate(self.connections.keys()):
            new_player = SnakePlayer(connection_id, self.SPAWN_POINTS[index][0], self.SPAWN_POINTS[index][1], self.game_mode_params["INIT_SNAKE_SIZE"])
            players[connection_id] = new_player
            #Tell the player the spawn points of everyone
            init_player_data = {}
            init_player_data["start_grid"] = self.SPAWN_POINTS[index][0]
            init_player_data["direction"] = self.SPAWN_POINTS[index][1]
            init_player_data["connection_id"] = connection_id
            init_player_data["init_snake_size"] = self.game_mode_params["INIT_SNAKE_SIZE"]
            init_player_data["color"] = SNAKE_COLORS[connection_id]
            init_player_data_all[connection_id] = init_player_data
            #Sleeping because something weird is going on and sometimes this command never gets to the clients
            time.sleep(0.1)
            #Tell the player their connection_id
            self.sendCommand(["CON_ID", connection_id], connection_id)
        
        #Sleeping because something weird is going on and sometimes this command never gets to the clients
        time.sleep(0.1)
        init_command = ["INIT_PLAYER_DATA", init_player_data_all]
        self.broadcastCommand(init_command)
        
        self.gameserver = GameServer(self, players)
        
        game_over = False
        game_init_start = True
        countdown = GAME_START_WAIT
        
        while self.quitting is False and game_init_start is True:
            #Initial countdown
            print "STARTING GAME IN %s SECONDS..." % countdown
            if countdown == 0:
                #GET IT ON!
                game_init_start = False
                #Make them all alive
                for _, p in self.gameserver.players.iteritems():
                    p.alive = True
                self.broadcastCommand(["SERVER_MESSAGE", "GAME STARTING!"])
            else:
                self.broadcastCommand(["SERVER_MESSAGE", "GAME STARTING IN %s SECONDS..." % countdown])
                countdown -= 1
            time.sleep(1)
            
        
        #GAME ON!!
        self.broadcastCommand(["GAME_START", None])
        
        #Generate first set of objectives
        
        while len(self.gameserver.objectives) < MAX_OBJECTIVES:
            self.gameserver.updateObjectives()
        
        while self.quitting is False and game_over is False:
            #Prune connections, if all clients have disconnected its game over
            self.checkConnections()
            if len(self.connections) == 0:
                print "All players disconnected, game over man!"
                game_over = True
                continue
            
            #Game stuff is inside this function
            self.gameserver.halfTick()
            #Sleep half the tickrate. I'm sure there is a better way to handle this but
            #basically every other tick we send updated data and the other ticks we get data.
            time.sleep(self.game_mode_params["TICKRATE_MS"]/2000.0)
        
        self.broadcastCommand(["SERVER_MESSAGE", "GAME OVER MAN!!"])
        self.broadcastCommand(["GAME_OVER"])
        self.quitting = True
        return True
        
    def checkConnections(self):
        bad_cons = []
        for connection_id, connection in self.connections.iteritems():
            if connection.quitting is True:
                bad_cons.append(connection_id)
        for connection_id in bad_cons:
            del(self.connections[connection_id])
            self.gameserver.updatePlayerState(connection_id, {"alive": False})
    
    def getConnection(self):  
        print "Waiting for players... Currently %s/%s" % (len(self.connections), MAX_PLAYERS)
        print "-----------------"
        readable, _, _ = select.select([self.main_socket, self.quit_socket], [], [], 60)
        for sock in readable:
            if sock == self.main_socket:
                connection, addy = sock.accept()
                connection.setblocking(1)
                #Create new thread to handle connection
                new_connection = ServerClientConnection(connection, self.closeConnectionCallback, self.dataUpdateCallback, self.nextidx)
                #Add our connection_thread to our connection tracker
                self.connections[self.nextidx] = new_connection
                self.nextidx += 1
            elif sock == self.quit_socket:
                self.quit_socket.accept()
                self.quit_socket.close()
                self.quitting = True
                return True
            continue
    
    def networkCleanup(self):
        #make sure everything has shut down
        self.stopClientThreads()
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
            self.getConnection()
        if self.quitting is False:
            print "All players are connected! Starting game in %s seconds..." % GAME_START_WAIT
            self.startGame()
        
        self.networkCleanup()
    

class ServerClientConnection(object):
    def __init__(self, client_socket, closeConnectionCallback, dataUpdateCallback, connection_id):
        self.client_socket = client_socket
        self.closeConnectionCallback = closeConnectionCallback
        self.dataUpdateCallback = dataUpdateCallback
        self.connection_id = connection_id
        self.quitting = False
        #super(ServerClientConnection, self).__init__()
        
    def quitThread(self):
        self.quitting = True
        self.client_socket.close()
        self.closeConnectionCallback(self.connection_id)
        
    def sendCommand(self, command, recv=False):
        try:
            #Depending on the command, we may want to wait for data as well
            self.client_socket.send(command)
            if recv is True:
                d = self.receiveData()
                if d is not None:
                    d = cPickle.loads(d)
                    #Tell the main thread we got some data for it
                    self.dataUpdateCallback(self.connection_id, d)
                else:
                    print "SCC_DBG: Didnt get expected return data. Ruh Roh."
        except Exception as e:
            if e.args[0] in [10053, 10054, 9]:
                print "\n[%s] SCC_DEBUG: Client connection closed, we're done." % self.connection_id
                self.quitThread()
            else:
                print "\n[%s] SCC_DEBUG: Something went terribly wrong here, Exception was:" % self.connection_id
                import traceback
                traceback.print_exc()
            
    
    def receiveData(self):
        data = None
        try:
            readable, _, _ = select.select([self.client_socket], [], [], 1) #Very low timeout, we should get data right away
            for sock in readable:
                data = sock.recv(4096)
                if data is not None and len(data) > 0:
                    return data
                elif len(data) == 0:
                    print "SCC_DBG: Connection error, quitting..."
                    self.quitThread()
                else:
                    return None
        except:
            self.quitThread()
        


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
    
    def getInitPlayerData(self):
        while self.client_thread.init_player_data is None:
            time.sleep(0.25) #I dont like using sleep here, theres probably a better way to do this with callbacks.
        return self.client_thread.init_player_data
    
    
    #The client's connection_id should be set as long as this is called after getInitPlayerData().
    def getConnectionID(self):
        return self.client_thread.connection_id
        
    def setSnakeReference(self, snake_reference):
        self.client_thread.snake_reference = snake_reference
        
    def setGridReference(self, grid_reference):
        self.client_thread.grid_reference = grid_reference
    

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
            network_thread.networkCleanup()
            network_thread.join()
            network_thread = None
    else:
        print "%s: Networking thread is not currently running." % network_thread.name

