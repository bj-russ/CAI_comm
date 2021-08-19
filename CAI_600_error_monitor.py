#This controls the automation of the PAG varification system. 
import sys
import json
import datetime
import time
import AK_format
#import AK_commands as com
import socket
import pandas as pd
import os.path
from os import path
import statistics
import CAI_600_functions

with open('config.json') as json_file:
    settings = json.load(json_file)




if __name__ == '__main__':
    CAI_1 = CAI_600_functions.CAI_600("CAI_1", settings["CAI_1"])
    completed = 0
    try:
        while True:
            time_current = datetime.datetime.now()
            hour_current = time_current.strftime("%H:%M")   
            scheduled_time = CAI_1.scheduled_time     
            initiate, completed = CAI_1.timer(completed, scheduled_time, hour_current)
            if initiate:
                print("Test Initiated")
                CAI_1.HFID_automate()
            else:
                t_until_next, unit = CAI_1.time_until_next_test(scheduled_time)
                print('Next test scheduled for ' + scheduled_time + ' Test will be started in ' + str(t_until_next), unit, end ='\r')
                time.sleep(10)
        
    except KeyboardInterrupt:
        print("caught keyboard interrupt, exiting")