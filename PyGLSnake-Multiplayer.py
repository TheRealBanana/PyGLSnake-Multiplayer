
from OpenGL.GL import glColor3ub, glVertex2i, glBegin, glEnd, glClearColor, GL_QUADS, glClear, GL_COLOR_BUFFER_BIT
from OpenGL.GLU import gluOrtho2D
from OpenGL.GLUT import glutTimerFunc, glutSpecialFunc, glutInit, glutInitDisplayMode, glutPostRedisplay, glutInitWindowSize, glutInitWindowPosition, glutSwapBuffers, glutCreateWindow, glutDisplayFunc, glutMainLoop, GLUT_DOUBLE, GLUT_RGB, glutSetOption, GLUT_ACTION_ON_WINDOW_CLOSE, GLUT_ACTION_CONTINUE_EXECUTION
#from time import sleep, time
from math import floor
import sys
import re
from os import listdir as os_listdir
from snake_logic import SnakeManager
from network import MasterNetworkMode


#Defaults, these will either be overwritten with server-supplied values in ClientMode
#or these will serve as the values other clients use when in ServerMode.
WINDOW_SIZE = (500,500)
GRID_SIDE_SIZE_PX = 20
TICKRATE_MS = 200
MATH_PRECISION = 5
#maximum number of active objective blocks on the grid at one time
MAX_ACTIVE_OBJS = 7
#Delay between objectives being added to the grid, in ticks (i.e. number of snake moves between adding new objectives)
OBJECTIVE_DELAY_TICKS = 10
#Starting snake size
INIT_SNAKE_SIZE = 5

#Just makes things look nicer
CORNER_ANGLES = {
    "tl": 45,
    "bl": 135,
    "br": 225,
    "tr": 315
}

#Defines the color of each type of element
ELEMENT_TYPES = []
ELEMENT_TYPES.append([0, 0, 0]) # Type # 0; DEFAULT_COLOR
ELEMENT_TYPES.append([255, 255, 255]) # Type # 1; SNAKE_HEAD
ELEMENT_TYPES.append([255, 255, 255]) # Type # 2; SNAKE_TAIL
ELEMENT_TYPES.append([0, 84, 166]) # Type # 3; OBJECTIVE
ELEMENT_TYPES.append([255, 0, 0]) # Type # 4; DEAD HEAD


#Our snake color will correspond to our connection_id. Will probably only have 6 colors to start with
#simple list using connection_id as index will suffice

class Grid(object):
    def __init__(self, snake_manager_reference, grid_side_size_px=GRID_SIDE_SIZE_PX, window_size=WINDOW_SIZE):
        super(Grid, self).__init__()
        self.rows = int(floor(window_size[0]/grid_side_size_px))
        self.cols = int(floor(window_size[1]/grid_side_size_px))
        self.grid_side_size_px = grid_side_size_px
        self.snake_manager_reference = snake_manager_reference
        self.active_grid_elements = {}
        self.objective_elements = {}
        
    def getGridElement(self, grid_index_tuple):
        if self.active_grid_elements.has_key(grid_index_tuple):
            return self.active_grid_elements[grid_index_tuple]
        else:
            return None
    
    def createGridElement(self, element_color, grid_index_tuple):
        #Figure out the coords of the top-left corner
        x_coord = self.grid_side_size_px * grid_index_tuple[0] + self.grid_side_size_px
        y_coord = self.grid_side_size_px * grid_index_tuple[1] + self.grid_side_size_px
        new_grid_element = GridElement(self.grid_side_size_px, (x_coord, y_coord), element_color)
        self.active_grid_elements[grid_index_tuple] = new_grid_element
    
    def deleteGridElement(self, grid_index_tuple):
        if self.active_grid_elements.has_key(grid_index_tuple):
            del(self.active_grid_elements[grid_index_tuple])
            return True
        else:
            #Replace-me after debugging
            raise Exception("Tried to delete non-existent grid element at index %s" % repr(grid_index_tuple))
            #return False
    
    def clearGrid(self):
        del(self.active_grid_elements) #I dont trust the GC sometimes. Doesnt hurt anyway.
        self.active_grid_elements = {}
    
    #Go through all snake data and update the grid with it
    #I am kind of stumped here with how I should proceed. I wanted to just update
    #the grid elements that needed to be updated but I would have to recode so much
    #of the work I *just* did to make that happen.
    #The only alternative is to recreate *every* element, *every* frame. Thats kinda lame.
    #Luckily our framerate is like 5fps at 200ms tickrate so its not a major issue for now.
    def updateGrid(self):
        self.clearGrid()
        all_snake_data = self.snake_manager_reference.getAllSnakesData()
        for connection_id, snake_data in all_snake_data.iteritems():
            #Update the element type list with this snake's specific colors
            ELEMENT_TYPES[1] = snake_data["color"][0]
            ELEMENT_TYPES[2] = snake_data["color"][1]
            #Now loop through the snake grids and set them
            #Our snake head is always the last item in the list (index -1)
            snake_head = snake_data["snake_grids"].pop(-1)
            self.createGridElement(ELEMENT_TYPES[1], snake_head)
            for grid in snake_data["snake_grids"]:
                self.createGridElement(ELEMENT_TYPES[1], grid)
        
        #Add our objectives to our active element list
        self.active_grid_elements.update(self.objective_elements)
    

class GridElement(object):
    def __init__(self, size_side_px, origin_coords, color):
        super(GridElement, self).__init__()
        self.color = color
        self.origin_coords = origin_coords
        self.size_px = size_side_px
        
    def getVertices(self):
        return_vertices = {}
        #Building from the bottom right corner.
        return_vertices["br"] = (self.origin_coords[0], self.origin_coords[1])
        return_vertices["tr"] = (self.origin_coords[0], self.origin_coords[1]-self.size_px)
        return_vertices["tl"] = (self.origin_coords[0]-self.size_px, self.origin_coords[1]-self.size_px)
        return_vertices["bl"] = (self.origin_coords[0]-self.size_px, self.origin_coords[1])
        
        return return_vertices
    
    
    def draw(self):
        vertices = self.getVertices()
        glColor3ub(*self.color)
        glBegin(GL_QUADS)
        glVertex2i(*vertices["tl"])
        glVertex2i(*vertices["bl"])
        glVertex2i(*vertices["br"])
        glVertex2i(*vertices["tr"])
        glEnd()



class RenderManager(object):
    def __init__(self, grid_instance, snake_instance, network_instance):
        super(RenderManager, self).__init__()
        self.grid_instance = grid_instance
        self.snake_instance = snake_instance
        self.network_instance = network_instance
    
    def calc_movement_all_shapes(self, _):
        #Snake logic, best logic
        
        self.network_instance.game_tick()
        #self.snake_instance.game_tick()
        
        #Reset our timer
        glutTimerFunc(TICKRATE_MS, self.calc_movement_all_shapes, 0)
        
        #Tell glut to rerun our display function
        glutPostRedisplay()
    
    def render_all_shapes(self):
        glClear(GL_COLOR_BUFFER_BIT)
        #Update our game grid before we draw
        self.grid_instance.updateGrid()
        for _, s in self.grid_instance.active_grid_elements.iteritems():
            s.draw()
        glutSwapBuffers()

def glinit(title="PyGLSnake-Multiplayer"):
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB)
    glutInitWindowSize(*WINDOW_SIZE)
    glutInitWindowPosition(50,50)
    glutCreateWindow(title)
    glClearColor(*(ELEMENT_TYPES[0]+[255])) #All our colors are 3-ints, this one needs alpha channel too so we just tack it on
    gluOrtho2D(0, WINDOW_SIZE[0], WINDOW_SIZE[1], 0)


def load_settings():
    #Check if we even have a settings file in our current working directory.
    #If not then we default to server mode.
    filelist = os_listdir(".")
    settings = {}
    default_settings = {}
    default_settings["net_mode"] = "ServerMode"
    default_settings["ip"] = "0.0.0.0" # listen for outside connections on all available network interfaces
    default_settings["port"] = "auto" # Will find an available port and report it to the user
    ######
    # Future server settings, not implementing now:
    #default_settings["max_players"] = "3" #How many players before we start the game?
    #default_settings["max_ping"] = "25" #how many ms ping before we kick a player from the game
    #default_settings["game_mode"] = "standard" #Variants of the game. Do the killed players' snakes stay on the grid? Does the speed increase periodically? That kinda stuff.
    
    if "pyglsnakemulti.ini" in filelist:
        with open("pyglsnakemulti.ini", "r") as settingsfile:
            for line in settingsfile:
                goodline = re.match("(.*?)(?:\s+)?=(?:\s+)?(.*)", line)
                if goodline is not None:
                    settings[goodline.group(1)] = goodline.group(2)
    
    #Do we have the goods?
    good = False
    if settings.has_key("net_mode") is True:
        if settings["net_mode"] == "ClientMode" or settings["net_mode"] == "ServerMode":
            #Check for game mode params if we are server mode
            if settings["net_mode"] == "ServerMode":
                settings["game_params"] = {}
                settings["game_params"]["WINDOW_SIZE"] = WINDOW_SIZE
                settings["game_params"]["GRID_SIDE_SIZE_PX"] = GRID_SIDE_SIZE_PX
                settings["game_params"]["TICKRATE_MS"] = TICKRATE_MS
                settings["game_params"]["MATH_PRECISION"] = MATH_PRECISION
                settings["game_params"]["INIT_SNAKE_SIZE"] = INIT_SNAKE_SIZE
            else:
                settings["game_params"] = None
            #Check both for ip and port
            if settings.has_key("ip") is True and settings.has_key("port") is True:
                good = True
    if good is False:
        settings = default_settings
    
    return settings




def update_params(params):
    global WINDOW_SIZE, GRID_SIDE_SIZE_PX, TICKRATE_MS, MATH_PRECISION, INIT_SNAKE_SIZE
    WINDOW_SIZE = params["WINDOW_SIZE"]
    GRID_SIDE_SIZE_PX = params["GRID_SIDE_SIZE_PX"]
    TICKRATE_MS = params["TICKRATE_MS"]
    MATH_PRECISION = params["MATH_PRECISION"]
    INIT_SNAKE_SIZE = params["INIT_SNAKE_SIZE"]
    
def main():
    #Load up the local settings
    game_settings = load_settings()
    #Network starts first since it gives us many of the parameters we need to initialize our game grid.
    network = MasterNetworkMode(game_settings)
    network.startNetwork()
    
    #Client-side game related stuffs below
    #This function will wait until the network thread either connects or times out
    #This really shouldn't take more than a few hundred milliseconds at worst on a local connection
    
    game_grid_params = network.getParameters()
    if game_grid_params is None: #YOU DUN GOOFED UP NOW
        print "Failed to initialize network thread. Quitting..."
        exit(1)
    
    
    '''
    if game_settings["net_mode"] == "ClientMode":
        print "Client recv params:"
        print game_grid_params
    '''
    
    
    #Update our globals
    update_params(game_grid_params)
    #Get our player init data from the client thread.
    init_player_data = network.getInitPlayerData()
    client_connection_id = network.getConnectionID()
    #initilize our game grid and SnakeManager objects using the data gathered above.
    snakepit = SnakeManager(client_connection_id, init_player_data)
    Game_Grid = Grid(snakepit, game_grid_params["GRID_SIDE_SIZE_PX"], game_grid_params["WINDOW_SIZE"])
    
    
    #Update our network side with the SnakeManager reference
    network.setSnakeReference(snakepit)
    
    #class to handle the drawing of our various elements
    #This has turned into more of a driver class for everything.
    renderman = RenderManager(Game_Grid, snakepit, network)
    
    
    #Gl/Glut stuffs below
    glinit("PyGLSnake-Multiplayer :: Connection ID: %s" % client_connection_id)
    glutSpecialFunc(snakepit.keypressCallbackGLUT)
    #glutDisplayFunc is the main callback function opengl calls when GLUT determines that the display must be redrawn
    glutDisplayFunc(renderman.render_all_shapes)
    #This timer will execute our function every TICKRATE_MS milliseconds, and in this function we call glutPostRedisplay to invoke the above callback.
    glutTimerFunc(TICKRATE_MS, renderman.calc_movement_all_shapes, 0)
    #Might want to get rid of this unless we plan to run it through the komodo profiler
    glutSetOption(GLUT_ACTION_ON_WINDOW_CLOSE, GLUT_ACTION_CONTINUE_EXECUTION)
    #Start everything up
    glutMainLoop()



main()
# End of Program 
