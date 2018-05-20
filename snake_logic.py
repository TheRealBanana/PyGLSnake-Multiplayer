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
    #This will also cause our snake to move one grid
    def getOurSnakeData(self):
        #Get our next move based on our current direction
        next_move = self.snakes[self.our_connection_id].getMove()
        self.snakes[self.our_connection_id].setNextMove(next_move)
        return_data = self.snakes[self.our_connection_id].getSnakeState()
        return return_data
    

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
