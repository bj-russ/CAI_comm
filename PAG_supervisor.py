#This controls the automation of the PAG varification system. 

import datetime
import AK_handler
import socket
import pandas as pd

#load settings from config.cfg
config = pd.read_csv('config.csv')
HOST = config.host 
PORT = config.port 

print(HOST, PORT)
