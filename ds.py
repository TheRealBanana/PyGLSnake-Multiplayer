#Simple server, needed something without all the GL crap to make testing easier

from network import ServerMode

params = {}
params["WINDOW_SIZE"] = (500,500)
params["GRID_SIDE_SIZE_PX"] = 20
params["TICKRATE_MS"] = 200
params["MATH_PRECISION"] = 5
params["INIT_SNAKE_SIZE"] = 5

if __name__ == "__main__":
    server = ServerMode("0.0.0.0", 33450, params)
    server.start()
    