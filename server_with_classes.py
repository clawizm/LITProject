import socket
from led_manager_with_classes import LEDPanels
import time
import board
import neopixel
import math
import threading
import pickle
import typing
from multiprocessing import Process

class LITSubsystemServer:

    def __init__(self, lit_subsystem_leds: LEDPanels, port: int, host: str=''):
        self.lit_subsystem_leds = lit_subsystem_leds
        self.host = host
        self.port = port
        self.s: socket.socket = None

    def create_server(self):
        if self.s:
            return 
        self.s = socket.socket()
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #avoid reuse error msg
        self.s.bind(('', self.port))
        print("Server started. Waiting for connection...")
        self.s.listen(5)
        return
    
    def main_server_loop(self):
        if not self.s:
            self.create_server()
        c, addr = self.s.accept()
        print("Connection from: ",addr)
        self.s.send('Connected!'.encode()) #This may need to be deleted
        while True:
            #data is in bytes format, use decode() to transform it into a string
            data = c.recv(4096)
            if not data:
                break
            self.lit_subsystem_leds.update_leds_from_data_packets(data)
        self.main_server_loop()
        print("Disconnected. Exiting.")

def run_lit_subsystem_servers_in_parallel(lit_servers: typing.Union[list[LITSubsystemServer], LITSubsystemServer]):
    if isinstance(lit_servers, LITSubsystemServer):
        lit_servers.main_server_loop()
        
    elif isinstance(lit_servers, list):
        server_processes = [Process(target=lit_server.main_server_loop) for lit_server in (lit_servers)]
        for process in server_processes:
            process.start()

        for process in server_processes:
            process.join()
    return 