#This controls the automation of the PAG varification system. 

import datetime
import time
import AK_format
#import AK_commands as com
import socket
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

def comms_wrapper(msg, ext, err, s, errors):
    ak_convert = AK_format.ak_handler()
    msg_ak = ak_convert.build_command(msg)
    outb = msg_ak.encode()
    send_success = False
    err_count = 0
    while send_success != True and not err:  
        #send message
        s.sendall(outb)
        print("Sending", repr(outb), "to connection", HOST, PORT)
        #get resposne
        data = s.recv(1024)
        print("Received", repr(data))
        #rsp_ak = ser.read(8)
        rsp_ak = ""
        rsp = ak_convert.demolish_response(data.decode())                
        #check for errors
        if rsp[0] == '????':
            #case where faulty transfer was received, resend command
            print("Response indicates error with command, resending command...")
            outb = msg_ak.encode()
            err_count +=1
            if err_count >= 5:
                print('5 consecutive response errors were received, exiting...')
                err = True
                log('Comms Error', 'Multiple Retries')
                return err, rsp

        elif rsp[1] != '0':
            #case where an error occurs
            #send error command and check error ASTF and proceed accordingly
            msg_err = ['ASTF', 'K0']
            msg_err_ak = ak_convert.build_command(msg_err)
            s.sendall(msg_err_ak.encode())
            data = s.recv(1024)
            rsp = ak_convert.demolish_response(data.decode())
            error_str = errors.loc[(errors['Code'] == int(rsp[1]),'Error')].item()
            print('The HFID returned the following error :' + error_str + ' The scheduled test will be exited.')
            err = True
            log('HFID Error', error_str)
            return err, rsp

        else:
            send_success = True
            return err, rsp

def HFID_automate():        #this controls the varification procedure for HFID and returns the reading.
    ext = False
    err = False
    commands = [[]]
    df = pd.read_csv('HFID_sequence.csv', names = ['Command', 'Condition'])    #update with sequence once functional
    commands_ls = df['Command'].tolist()
    condition = df['Condition'].tolist()
    for i in commands_ls:
        commands.append(i.split(' '))
    commands = commands[1:]
    errors = pd.read_csv('errors.csv', names = ['Code', 'Error'])
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        while len(commands) != 0 and not ext and not err:
            #get next message
            msg = commands.pop(0)
            cond = condition.pop(0)
            #send message
            err, rsp = comms_wrapper(msg, ext, err, s, errors)
            cond_int = int(cond)
            #if cond == '0': #no condition, proceed to next command
            #    print('cond == 0')
            if not err:
                if cond_int == 1: #check oven temp >180C
                    t_oven = 0
                    while t_oven < 180:
                        msg1 = ['ATEM','K0']
                        err, rsp = comms_wrapper(msg1, ext, err, s, errors)
                        t_oven = int(rsp[3])
                        if t_oven < 180:
                            print("The oven temperature is currently " + str(t_oven) +". Waiting for temperature to reach >=180C before proceeding.")
                            time.sleep(10)
                        else:
                            print("The oven temperature is currently " + str(t_oven) +". Proceeding to next step.")
                elif cond_int == 2: #monitor fuel and air pressures, compare with instrument spec sheet.
                    t = 0
                    while t < 10:
                        msg2 = ['ADRU', 'K0']
                        err, rsp = comms_wrapper(msg2, ext, err, s, errors)
                        print("The air and fuel pressures are " + rsp[3] +", " + rsp[4] + " psi respectively. Waiting 5 seconds to recheck before proceeding")
                        time.sleep(5)
                        t += 5

                elif cond_int == 3: #Wait 1 hr for warm-up. Check burner temps
                    t_remaining = 10
                    while t_remaining >= 0:
                        msg3 = ['ATEM', 'K0']
                        err, rsp = comms_wrapper(msg3, ext, err, s, errors)
                        t_burner = int(rsp[4])
                        print("Waiting for burner to reach operating temp during 1 hr warmup. The current burner temp is " + str(t_burner) +". there is " +str(t_remaining) +"s remaining in the warmup period.")
                        time.sleep(5)
                        t_remaining -= 5
                else:
                    pass
            else:
                pass

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
            print('Waiting for scheduled time')
            time.sleep(1)
        
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")