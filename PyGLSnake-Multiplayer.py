
from OpenGL.GL import glColor3ub, glVertex2i, glBegin, glEnd, glClearColor, GL_QUADS, glClear, GL_COLOR_BUFFER_BIT
from OpenGL.GLU import gluOrtho2D
from OpenGL.GLUT import glutTimerFunc, glutSpecialFunc, glutInit, glutInitDisplayMode, glutPostRedisplay, glutInitWindowSize, glutInitWindowPosition, glutSwapBuffers, glutCreateWindow, glutDisplayFunc, glutMainLoop, GLUT_DOUBLE, GLUT_RGB, glutSetOption, GLUT_ACTION_ON_WINDOW_CLOSE, GLUT_ACTION_CONTINUE_EXECUTION
#from time import sleep, time
from math import floor
import sys
import re
from os import listdir as os_listdir
from snake_logic import Snake
from network import MasterNetworkMode


#We should index each grid element from the top-right corner instead of the top-left.
#This solves over-draw on right side while left side is immune since its the origin.
#How to implement?
#Must have before this will work properly, otherwise mismatched window size/grid size will cause major issues
#Maybe we should even reference from the bottom right, to prevent overdraw on both the right AND bottom.

WINDOW_SIZE = (500,500)
GRID_SIDE_SIZE_PX = 25
TICKRATE_MS = 200
MATH_PRECISION = 5

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
ELEMENT_TYPES.append([66, 255, 0]) # Type # 1; SNAKE_HEAD
ELEMENT_TYPES.append([40, 150, 0]) # Type # 2; SNAKE_TAIL
ELEMENT_TYPES.append([0, 84, 166]) # Type # 3; OBJECTIVE
ELEMENT_TYPES.append([255, 0, 0]) # Type # 4; DEAD HEAD


class Grid(object):
    def __init__(self, grid_side_size_px=GRID_SIDE_SIZE_PX):
        super(Grid, self).__init__()
        self.rows = int(floor(WINDOW_SIZE[0]/GRID_SIDE_SIZE_PX))
        self.cols = int(floor(WINDOW_SIZE[1]/GRID_SIDE_SIZE_PX))
        self.grid_side_size_px = grid_side_size_px
        self.active_grid_elements = {}
        
    def get_grid_element(self, grid_index_tuple):
        if self.active_grid_elements.has_key(grid_index_tuple):
            return self.active_grid_elements[grid_index_tuple]
        else:
            return None
    
    def create_grid_element(self, element_type, grid_index_tuple):
        #Figure out the coords of the top-left corner
        x_coord = self.grid_side_size_px * grid_index_tuple[0]
        y_coord = self.grid_side_size_px * grid_index_tuple[1]
        new_grid_element = GridElement(self.grid_side_size_px, (x_coord, y_coord), element_type)
        self.active_grid_elements[grid_index_tuple] = new_grid_element
    
    def delete_grid_element(self, grid_index_tuple):
        if self.active_grid_elements.has_key(grid_index_tuple):
            del(self.active_grid_elements[grid_index_tuple])
            return True
        else:
            #Replace-me after debugging
            raise Exception("Tried to delete non-existent grid element at index %s" % repr(grid_index_tuple))
            #return False
    
    def clear_grid(self):
        self.active_grid_elements = {}

class GridElement(object):
    def __init__(self, size_side_px, origin_coords, element_type):
        super(GridElement, self).__init__()
        self.type = element_type
        self.color = ELEMENT_TYPES[element_type]
        self.origin_coords = origin_coords
        self.size_px = size_side_px
        
    def get_vertices(self):
        return_vertices = {}
        
        return_vertices["tl"] = (self.origin_coords[0], self.origin_coords[1])
        return_vertices["bl"] = (self.origin_coords[0], self.origin_coords[1]+self.size_px)
        return_vertices["br"] = (self.origin_coords[0]+self.size_px, self.origin_coords[1]+self.size_px)
        return_vertices["tr"] = (self.origin_coords[0]+self.size_px, self.origin_coords[1])
        
        return return_vertices
    
    
    def draw(self):
        vertices = self.get_vertices()
        glColor3ub(*self.color)
        glBegin(GL_QUADS)
        glVertex2i(*vertices["tl"])
        glVertex2i(*vertices["bl"])
        glVertex2i(*vertices["br"])
        glVertex2i(*vertices["tr"])
        glEnd()



class RenderManager(object):
    def __init__(self, grid_instance, snake_instance):
        super(RenderManager, self).__init__()
        self.grid_instance = grid_instance
        self.snake_instance = snake_instance
    
    def calc_movement_all_shapes(self, _):
        #Snake logic, best logic
        self.snake_instance.game_tick()
        
        #Reset our timer
        glutTimerFunc(TICKRATE_MS, self.calc_movement_all_shapes, 0)
        
        #Tell glut to rerun our display function
        glutPostRedisplay()
    
    def render_all_shapes(self):
        glClear(GL_COLOR_BUFFER_BIT)
        for _, s in self.grid_instance.active_grid_elements.iteritems():
            s.draw()
        glutSwapBuffers()

def glinit():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB)
    glutInitWindowSize(*WINDOW_SIZE)
    glutInitWindowPosition(50,50)
    glutCreateWindow("PyGLSnake-Multiplayer")
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
            if settings.has_key("ip") is True and settings.has_key("port") is True:
                good = True
    if good is False:
        settings = default_settings
    
    return settings


def main():
    
    #Game related stuffs
    Game_Grid = Grid()
    snake = Snake(Game_Grid)
    #class to handle the drawing of our various elements
    renderman = RenderManager(Game_Grid, snake)
    game_settings = load_settings()
    network = MasterNetworkMode(renderman, game_settings)
    #Start up the network side
    network.startNetwork()
    
    #Gl/Glut stuffs below
    glinit()
    glutSpecialFunc(snake.keypress_callback_GLUT)
    glutDisplayFunc(renderman.render_all_shapes)
    glutTimerFunc(TICKRATE_MS, renderman.calc_movement_all_shapes, 0)
    glutSetOption(GLUT_ACTION_ON_WINDOW_CLOSE, GLUT_ACTION_CONTINUE_EXECUTION)
    #Start everything up
    glutMainLoop()



main()
# End of Program 
