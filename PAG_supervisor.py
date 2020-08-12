#This controls the automation of the PAG varification system. 
import sys
import datetime
import time
import AK_format
#import AK_commands as com
import socket
import pandas as pd
import os.path
from os import path
import statistics

#load settings from config.cfg


config = pd.read_csv('config.csv')
HOST = config.iloc[0,0]
PORT = config.iloc[0,1]
test_scheduled_time = config.iloc[0,2] 
#add additional settings here

ext = False
err = False
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
errors = pd.read_csv('errors.csv', names = ['Code', 'Error'])

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

def time_until_next_test(test_scheduled_time):      #hours only
    hr = int(test_scheduled_time[:2])               #update this to split hr then convert to int
    now = datetime.datetime.now().hour
    time_current = datetime.datetime.now()
    hour_current = now   
    unit = 'hrs'
    t_until_next = hr - now
    if t_until_next < 0:
        t_until_next += 24
    if t_until_next == 1:
        now = datetime.datetime.now().minute
        t_until_next = 60 - now
        unit = 'mins'
    return t_until_next, unit

def comms_wrapper(msg):
    global ext, err, s, errors
    ak_convert = AK_format.ak_handler()
    msg_ak = ak_convert.build_command(msg)
    outb = msg_ak.encode()
    send_success = False
    err_count = 0
    while send_success != True and not err:  
        #send message
        s.sendall(outb)
        #get resposne
        data = s.recv(1024)
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
        # the following are listed in the 700 manual but not the 600. Add if required
        #elif rsp[2] has '#': #case where the displayed value is not valid on the instrument
         #   pass

        #elif resp[3] == 'NA': #case where the channel does not exist
        #    pass

        #elif rsp[2] == 'SE': #case where a syntax error occured
            #pass

        else:
            send_success = True
            return err, rsp

def HFID_automate():
    global ext, err, s
    # Reset PAG condition indicators to Off
    with s:
        s.connect((HOST, PORT))
        #Set Remote
        err, rsp = comms_wrapper(['SREM', 'K0'])
        #Check Oven Temp
        if not err:
            t_oven = 0
            while t_oven < 180:
                msg = ['ATEM','K0']
                err, rsp = comms_wrapper(msg)
                t_oven = int(rsp[3])
                if t_oven < 180:
                    print("Waiting for oven temperature to reach > 180 C before proceeding.")
                    print("    The oven temperature is currently", str(t_oven),"C", end = '\r')
                    time.sleep(1)
                else:
                    print("The oven temperature is currently " + str(t_oven) +". Proceeding to next step.")
        # Ignite
        if not err:
            msg = ['STBY','K0']
            err, rsp = comms_wrapper(msg) 
            print("Burner ignition process started.")
        #monitor air/fuel pressures
        if not err:
            t = 10
            air = []
            fuel = []
            air_pass_condition = [10, 13]
            fuel_pass_condition = [10, 13]
            print("Monitoring air and fuel pressure during startup.")
            #print("Air Pressure,", "Fuel Pressure")
            while t > 0:
                msg = ['ADRU', 'K0']
                err, rsp = comms_wrapper(msg)
                if not err:
                    air.append(float(rsp[3].replace("'","")))
                    fuel.append(float(rsp[4].replace("'","")))
                print('    Air pressure is', rsp[3], 'psi. Fuel pressure is', rsp[4], 'psi. Time remaining =',t,' ', end='\r')
                time.sleep(1)
                t -= 1                               
            air_avg = sum(air[-5:]) / len(air[-5:])
            fuel_avg = sum(fuel[-5:]) / len(fuel[-5:])
            if air_pass_condition[0] < air_avg and air_pass_condition[1] > air_avg and fuel_pass_condition[0] < fuel_avg and fuel_pass_condition[1] > fuel_avg:
                print('The air and fuel delivery pressures are within spec.                               ')
            else:
                print("The air or fuel delivery pressure are out of spec.                                ")
                log("Error", "Pressure Failure, Air = " + str(air_avg) + ", Fuel = " + str(fuel_avg))
                err = True               
        # 1 hr warmup
        if not err:
            t_remaining = 10 #3600
            t_burner_min = 350
            print("Burner Warmup Started")
            #print("Reading, ", "Time Remaining")
            while t_remaining >= 0:
                msg = ['ATEM', 'K0']
                err, rsp = comms_wrapper(msg)
                t_burner = int(rsp[4])
                print('    Burner temperature is', t_burner,'C. Time remaining =',t_remaining,' ', end='\r')
                time.sleep(1)
                t_remaining -= 1
            if t_burner > t_burner_min:
                print("The burner has successfully preheated.                     ")
            else:
                print("The burner failed to preheat.                       ")
                log("Error", "Burner preheat failure. T_burner =" +str(t_burner))
        # Set Manaul Range mode
        if not err:
            err, rsp = comms_wrapper(['SARA', 'K0']) 
        # Set Range
        if not err:
            err, rsp = comms_wrapper(['SEMB', 'K0', '2']) # confirm range and how to select desired range
            print("The instrument range has been set to 2.")
        # Zero Calibration
        if not err:
            t_err =  300
            t = t_err
            readings = []
            complete = False
            stability_criteria = 0.1
            print("Zero Calibration Started")
            #print("Reading:")
            while t > 0 and not complete:
                msg = ['AKON', 'K0']
                err, rsp = comms_wrapper(msg)
                reading = rsp[2].replace("'",'')
                print('    The current reading is',reading,'ppm. Time remaining until error =',t,' ',end='\r')
                if t > t_err - 10: #build rolling average
                    readings.append(float(reading)) #assuming instrument in THC mode                            
                else:       #check rolling average for stability
                    readings.pop(0)
                    readings.append(float(reading))
                    average_reading = sum(readings) / len(readings)    
                    readings_std = statistics.stdev(readings)
                    print("The average reading is " + str(average_reading) + " and the std is " + str(readings_std) +'          ')
                    if 2*readings_std < stability_criteria:
                        #save cal value
                        msg2 = ['SNKA', 'K0']
                        err, rsp = comms_wrapper(msg2)
                        complete = True
                        print("The instrument was zeroed successfully")
                    else:
                        pass
                t -= 1
                time.sleep(1)
            if t == 0:
                print("The reading failed to stabilize in the alloted time. Exiting..      ")
                log("Error", "Failed to stabilize during zero calibration")
                err = True             
        # span calibration
        if not err:
            t_err = 300
            t = t_err
            readings = []
            complete = False
            stability_criteria = 0.1
            print("Span Calibration Started")
            while t > 0 and not complete:
                msg = ['AKON', 'K0']
                err, rsp = comms_wrapper(msg)
                reading = rsp[2].replace("'",'')
                print('    The current reading is',reading,'ppm. Time remaining until error =',t,' ',end='\r')
                if t > t_err - 10: #build rolling average
                    readings.append(float(reading)) #assuming instrument in THC mode                            
                else:
                    readings.pop(0)
                    readings.append(float(reading))
                    average_reading = sum(readings) / len(readings)    
                    readings_std = statistics.stdev(readings)
                    print("The average reading is " + str(average_reading) + " and the std is " + str(readings_std) +'          ')
                    if 2*readings_std < stability_criteria:
                        #save cal value
                        msg2 = ['SEKA', 'K0']
                        err, rsp = comms_wrapper(msg)
                        complete = True
                        print("The instrument was spanned successfully    ")                        
                    else:
                        pass
                t -= 1
                time.sleep(1)
            if t == 0:
                print("The reading failed to stabilize in the alloted time. Exiting..     ")
                log("Error", "Failed to stabilize during span calibration")
                err = True
        # Check PAG 1
        if not err:
            #set solenoid for PAG 1
            t_err = 6
            t = t_err
            readings = []
            complete = False
            stability_criteria = 0.1
            air_spec = 0.2
            print("PAG #1 Check Started")
            while t > 0 and not complete:
                msg = ['AKON', 'K0']
                err, rsp = comms_wrapper(msg)
                reading = rsp[2].replace("'",'')
                print('    The current reading is',reading,'ppm. Time remaining until error =',t,' ',end='\r')
                if t > t_err - 10: #build rolling average
                    readings.append(float(reading)) #assuming instrument in THC mode                            
                else:
                    readings.pop(0)
                    readings.append(float(reading))
                    average_reading = sum(readings) / len(readings)    
                    readings_std = statistics.stdev(readings)
                    print("The average reading is " + str(average_reading) + " and the std is " + str(readings_std) +'        ')
                    if 2*readings_std < stability_criteria: #reading is stable
                        if average_reading < air_spec:
                            #Store Reading and log test as successful
                            log("Test Result", "Successful completion. PAG #1 Air Reading = " + str(average_reading))                                
                            complete = True
                            print("PAG #1 is functioning as expected")
                            # Set PAG 1 indicator to PASS
                        else:
                            log("Test Results", "Test Failure. PAG #1 Air Reading = " + str(average_reading))
                            print("PAG #1 is NOT functioning")
                            complete = True
                            # Set PAG 1 indicator to FAIL
                    else:
                        pass
                t -= 1
                time.sleep(1)
            if t == 0:
                print("The reading failed to stabilize in the alloted time.              ")
                log("Error", "PAG #1 Failed to stabilize during reading")
            # Reset solenoid to neutral setting.
        # check PAG 2
        if not err:
            #set solenoid for PAG 2
            t_err = 300
            t = t_err
            readings = []
            complete = False
            stability_criteria = 0.1
            air_spec = 0.2
            print("PAG #2 Check Started")
            while t > 0 and not complete:
                msg = ['AKON', 'K0']
                err, rsp = comms_wrapper(msg)
                reading = rsp[2].replace("'",'')
                print('    The current reading is',reading,'ppm. Time remaining until error =',t,' ',end='\r')
                if t > t_err - 10: #build rolling average
                    readings.append(float(reading)) #assuming instrument in THC mode                            
                else:
                    readings.pop(0)
                    readings.append(float(reading))
                    average_reading = sum(readings) / len(readings)    
                    readings_std = statistics.stdev(readings)
                    print("The average reading is " + str(average_reading) + " and the std is " + str(readings_std) +'        ')
                    if 2*readings_std < stability_criteria: #reading is stable
                        if average_reading < air_spec:
                            #Store Reading and log test as successful
                            log("Test Result", "Successful completion. PAG #2 Air Reading = " + str(average_reading))                                
                            complete = True
                            print("PAG #2 is functioning as expected")
                            # Set PAG 2 indicator to PASS
                        else:
                            log("Test Results", "Test Failure. PAG #2 Air Reading = " + str(average_reading))
                            print("PAG #2 is NOT functioning")
                            complete = True
                            # Set PAG 2 indicator to FAIL
                    else:
                        pass
                t -= 1
                time.sleep(1)
            if t == 0:
                print("The reading failed to stabilize in the alloted time.              ")
                log("Error", "PAG #1 Failed to stabilize during reading")
            # reset solenoid to neutral position
        # Stop Fuel flow (When complete or if error occurs)
        if err: # reset error for shutdown comms
            err = False
        err, rsp = comms_wrapper(['SPAU', 'K0'])
        print("Fuel flow to instrument stopped.")
        # Purge analyser for 5 mins
        t_remaining = 15
        msg = ['SSPL', 'K0']
        err, rsp = comms_wrapper(msg)
        print("Purging instrument with air")
        while t_remaining >= 0:
            msg4 = ['AKON', 'K0']
            err, rsp = comms_wrapper(msg4)
            reading = rsp[2].replace("'",'')
            print('Reading =', reading, 'Time remaining = ' + str(t_remaining) +" s ", end='\r')
            time.sleep(1)
            t_remaining -= 1
        err, rsp = comms_wrapper(msg) #check if this also shuts off zero gas. If not set to whatever initial state is
        print("Purging complete                 ")   
        # Return instrument to manual mode
        err, rsp = comms_wrapper(['SMAN', 'K0'])
        print("Instrument returned to Manual mode. Test completed.")             

            

#main program operation
completed = 0 #used as indicator if test has been run already today
try:
    while True:
        time_current = datetime.datetime.now()
        hour_current = time_current.strftime("%H:%M")        
        initiate, completed = timer(completed, test_scheduled_time, hour_current)
        if initiate:
            print("Test Initiated")
            HFID_automate()
        else:
            t_until_next, unit = time_until_next_test(test_scheduled_time)
            print('Next test scheduled for ' + test_scheduled_time + ' Test will be started in ' + str(t_until_next), unit, end ='\r')
            time.sleep(10)
        
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")