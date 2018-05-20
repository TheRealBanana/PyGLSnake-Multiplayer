from random import randint

class SnakeManager(object):
    def __init__(self, our_connection_id, init_player_data_all={}):
        self.our_connection_id = our_connection_id
        self.snakes = {}
        for connection_id, init_player_data in init_player_data_all.iteritems():
            newsnake = Snake(init_player_data)
            self.snakes[connection_id] = newsnake
        super(SnakeManager, self).__init__()
    
    #Set a single variable for all players. For now it just sets them alive
    #Might do more later, who knows.
    def setAllPlayersVar(self, player_var, var_data):
        for connection_id, snakeobj in self.snakes.iteritems():
            if player_var == "alive":
                snakeobj.alive = var_data
    
    #Getting input from GLUT's special input func
    def keypressCallbackGLUT(self, keycode, _, __): #Last two args are the x and y coords but we dont care about them
        if keycode == 100: self.changeDirection("left")
        elif keycode == 101: self.changeDirection("up")
        elif keycode == 102: self.changeDirection("right")
        elif keycode == 103: self.changeDirection("down")
    
    #Update the direction of our own snake
    def changeDirection(self, newdir):
        our_snake = self.snakes[self.our_connection_id]
        if our_snake.alive == True:
            #Dont allow direction change in the direct opposite (run backwards)
            if our_snake.getMove(newdir) != our_snake.snake_grids[-2]:
                our_snake.direction = newdir
    
    #Set all the data for all snakes
    def setAllSnakesData(self, updated_player_data_all):
        for connection_id, snake_data in updated_player_data_all.iteritems():
            self.snakes[connection_id].setSnakeState(snake_data)
    
    #Get all the data for all snakes
    def getAllSnakesData(self):
        all_snake_data = {}
        for connection_id, snakeobj in self.snakes.iteritems():
            all_snake_data[connection_id] = snakeobj.getSnakeState()
        return all_snake_data
    
    #Just get our snake data
    def getOurSnakeData(self):
        #Get our next move based on our current direction
        next_move = self.snakes[self.our_connection_id].getMove()
        self.snakes[self.our_connection_id].setNextMove(next_move)
        return self.snakes[self.our_connection_id].getSnakeState()

class Snake(object):
    def __init__(self, init_player_data):
        super(Snake, self).__init__()
        self.connection_id = init_player_data["connection_id"]
        self.current_grid = init_player_data["start_grid"]
        self.direction = init_player_data["direction"]
        self.length = init_player_data["init_snake_size"]
        self.color = init_player_data["color"]
        self.snake_grids = [self.current_grid]
        self.alive = False
    
    def setSnakeState(self, snake_state_data):
        self.alive = snake_state_data["alive"]
        self.current_grid = snake_state_data["current_grid"]
        #self.direction = snake_state_data["direction"]
        self.length = snake_state_data["length"]
        self.snake_grids = snake_state_data["snake_grids"]
    
    def getSnakeState(self):
        return_state_data = {}
        return_state_data["connection_id"] = self.connection_id
        return_state_data["alive"] = self.alive
        return_state_data["current_grid"] = self.current_grid
        return_state_data["direction"] = self.direction
        return_state_data["length"] = self.length
        return_state_data["snake_grids"] = list(self.snake_grids) #ran into refernce passing issues so copying solves it
        return_state_data["color"] = self.color
        return return_state_data
    
    #Get the next move for our snake
    #This will not return any data, just update our current snake grids to include our new grid
    def getMove(self, direction=None):
        if direction is None:
            direction = self.direction
        
        if direction == "down":
            next_grid = (self.current_grid[0], self.current_grid[1]+1)
            
        elif direction == "up":
            next_grid = (self.current_grid[0], self.current_grid[1]-1)
            
        elif direction == "right":
            next_grid = (self.current_grid[0]+1, self.current_grid[1])
        
        elif direction == "left":
            next_grid = (self.current_grid[0]-1, self.current_grid[1])
        
        return next_grid
    
    def setNextMove(self, next_grid):
        if len(self.snake_grids) >= self.length:
            del(self.snake_grids[0])
        self.snake_grids.append(next_grid)
        self.current_grid = next_grid
        
        
    
    
    
    
    
    def game_tick(self):
        if self.gameover is False:
            self.current_mode()
            self.tickno += 1
        
    
    def snake_dead(self):
        #Color the snake head red to indicate we ded
        self.game_grid_instance.create_grid_element(4, self.current_grid)
        print "UGH WE DED"
        self.current_mode = self.game_over_mode
    
    def snake_mode(self):
        if self.direction == "None":
            #Just starting out. Do stuffs for just starting out...
            self.direction = "right"
            #Add half the max number of objectives to the grid at the start
            for _ in range(1,MAX_ACTIVE_OBJS/2):
                self.add_objective()
        
        
        #Add objective every OBJECTIVE_DELAY_TICKS ticks
        if self.tickno % OBJECTIVE_DELAY_TICKS == 0:
            self.add_objective()
        
        self.moveSnake()
        
        if self.alive == False:
            self.snake_dead()
    
    def game_over_mode(self):
        print "GAME OVER MAN"
        print "Final score: %s" % str(self.length - INIT_SNAKE_SIZE)
        self.gameover = True
    
    
    def collected_objective(self, grid):
        self.length += 1
        self.objective_list.remove(grid)
    
    
    def add_objective(self):
        #Should we remove one first?
        if len(self.objective_list) == MAX_ACTIVE_OBJS:
            self.game_grid_instance.delete_grid_element(self.objective_list.pop(0))
            
            
        #Generate a random grid number and make sure its not currently occupied
        obj_grid = (randint(0, self.game_grid_instance.rows), randint(0, self.game_grid_instance.cols))
        while obj_grid in self.snake_grids or obj_grid in self.objective_list:
            obj_grid = (randint(0, self.game_grid_instance.rows), randint(0, self.game_grid_instance.cols))
        self.objective_list.append(obj_grid)
        self.game_grid_instance.create_grid_element(3, obj_grid) #Mode 3 is our objective block
        
    
    def moveSnake(self):
        #Figure out the next grid from our current grid and our direction
        next_move = self.getMove()
        
        #Hit a wall, game over man. Game over!
        if ((0 <= next_move[0] < self.game_grid_instance.rows) and (0 <= next_move[1] < self.game_grid_instance.cols)) is False:
            self.alive = False
        
        #Hit ourself! X(
        elif next_move in self.snake_grids:
            self.alive = False
            
        #Hit other snake?? Ohshi-
            
        #good move
        else:
            #Move snake head, change old square color to snake body (state 7), cut off snake tail by changing to white if current snake size == max snake size
            self.game_grid_instance.create_grid_element(1, next_move) #Snake head is state 1
            self.game_grid_instance.create_grid_element(2, self.current_grid) #Snake tail is state 2
            
            self.snake_grids.append(next_move)
            
            #Check our length before we see if we collected an objective
            #Truncate our tail if we are too long
            if len(self.snake_grids) >= self.length:
                self.game_grid_instance.delete_grid_element(self.snake_grids.pop(0))
            
            if next_move in self.objective_list:
                self.collected_objective(next_move)
            
            self.current_grid = next_move
    

