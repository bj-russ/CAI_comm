#This controls the automation of the PAG varification system. 

import datetime
import AK_handler
#import AK_commands as com
import socket
import pandas as pd
import os.path
from os import path

#load settings from config.cfg
print(repr('/Users/Tom/Desktop/WFH/PAG Varification/PAG_varifier/config.csv'))

config = pd.read_csv('/Users/Tom/Desktop/WFH/PAG Varification/PAG_varifier/config.csv')
HOST = config.iloc[0,0]
PORT = config.iloc[0,1] 
#add additional settings here

#define functions

def log(status, reading):
    time = datetime.datetime.now()
    t = time.strftime("%Y %b %d %H:%M:%S")
    results = [t, status, reading]
    df = pd.DataFrame([results], columns=['Time of test', 'Test Result', 'Reading'])
    if path.isfile('PAG_log.csv'):
        df.to_csv('PAG_log.csv', mode = 'a', header=False)
    else:
        df.to_csv('PAG_log.csv', mode = 'a', header=True)

log('Pass', 0)