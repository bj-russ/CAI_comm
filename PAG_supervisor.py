#This controls the automation of the PAG varification system. 

import datetime
import time
import AK_format
#import AK_commands as com
import serial
import pandas as pd
import os.path
from os import path

#load settings from config.cfg


config = pd.read_csv('config.csv')
HOST = config.iloc[0,0]
PORT = config.iloc[0,1]
test_scheduled_time = config.iloc[0,2] 
#add additional settings here

#define functions

def log(status, reading):                               #This logs the varification events/results for future tracking.
    time = datetime.datetime.now()
    t = time.strftime("%b/%d/%Y, %H:%M:%S")
    results = [t, status, reading]
    df = pd.DataFrame([results], columns=['Time of test', 'Test Result', 'Reading'])
    if path.isfile('PAG_log.csv'):
        df.to_csv('PAG_log.csv', mode = 'a', header=False, index = False)
    else:
        df.to_csv('PAG_log.csv', mode = 'a', header=True, index = False)

def timer(completed, scheduled_time, current_time):     #This is used to initiate the varification based on a schedule.
        if completed == 0 and hour_current >= scheduled_time:  #if time is greater then scheduled time and test hasn't already been completed, run varification
            completed = 1
            return True, completed
        elif completed == 1 and hour_current == "00:00":                         #reset completed indicator for new day
            completed = 0
            return False, completed
        else:                                                                   #wait and reiterate 
            return False, completed                              

def HFID_automate():        #this controls the varification procedure for HFID and returns the reading.
    ext = False
    err = False
    ak_convert = AK_format.ak_handler()
    with serial.Serial('COM1') as ser:
        ser.baudrate = 9600
        ser.timeout = 1
        while ext != True and err != True:
            #get next message
            msg = ['AKON','K0']
            msg_ak = ak_convert.build_command(msg)
         
            #send message
            ser.write(msg_ak.encode())
            #get resposne
            #rsp_ak = ser.read(8)
            rsp_ak = ""
            rsp = ak_convert.demolish_response(rsp_ak)

            #check for errors





#main program operation
completed = 0
try:
    while True:
        time_current = datetime.datetime.now()
        hour_current = time_current.strftime("%H:%M")        
        initiate, completed = timer(completed, test_scheduled_time, hour_current)
        if initiate:
            print("Test Initiated")
            HFID_automate()
        else:
            time.sleep(1)
        
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")