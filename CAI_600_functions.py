import datetime
import time
import statistics
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
class CAI_600():
    def __init__(self, name, settings):
        self.name = name
        self.settings = settings
        self.HOST = settings["host"]
        self.PORT = int(settings["port"])
        self.log_file = settings["log_file"]
        self.scheduled_time = settings["scheduled_time"]
        self.ext = False
        self.err = False
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.errors = pd.read_csv('errors.csv', names = ['Code', 'Error'])
        self.error_text = ""

        self.ak_convert = AK_format.ak_handler()
    def log(self, status, reading):
        time = datetime.datetime.now()
        t = time.strftime("%b/%d/%Y, %H:%M:%S")
        results = [t, status, reading]
        df = pd.DataFrame([results], columns=['Time of test', 'Test Result', 'Reading'])
        if path.isfile(self.log_file):
            df.to_csv(self.log_file, mode = 'a', header=False, index = False)
        else:
            df.to_csv(self.log_file, mode = 'a', header=True, index = False)
    
    def timer(self, completed, scheduled_time, current_time): #taken from PAG_supervisor.py
        """Timer Function used to initiate verification based on a schedule

        Parameters:
        completed (int): keep track of if test has been completed during timed limit
        scheduled_time ("%H:%M"): scheduled time in between events. From config.json
        current_time ("%H:%M"): current time from datetime.datetime.now()

        Returns:
        bool: completed state
        int: completed state (0 for false, 1 for true)
        """
        if completed == 0 and current_time >= scheduled_time:  #if time is greater then scheduled time and test hasn't already been completed, run varification
            completed = 1
            return True, completed
        elif completed == 1 and current_time == "00:00":                         #reset completed indicator for new day
            completed = 0
            return False, completed
        else:                                                                   #wait and reiterate 
            return False, completed

    def time_until_next_test(self,test_scheduled_time): 
        """Calculates time until next test and returns the time
        Parameters:
        test_scheduled_time ()
        """     #hours only
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

    def comms_wrapper(self, msg):
        """ Sends PARAMETER(msg) to CAI unit and gets return

        Parameters:
        msg (['####', '##']): AK protocol message ['####', '##']

        Returns:
        err: bool (T/F)
        rsp: response message
        """
        
        msg_ak = self.ak_convert.build_command(msg)
        outb = msg_ak.encode()
        send_success = False
        err_count = 0
        
        while not send_success and not self.err:
            #send message
            self.s.sendall(outb)
            #getresponse
            data = self.s.recv(1024)
            rsp = self.ak_convert.demolish_response(data.decode())
            #check for errors
            if rsp[0] == '????':
                #case where faulty transfer was received, resend command
                self.error_text = "Response indicates error with command, resending command..."
                print(self.error_text)
                outb = msg_ak.encode()
                err_count+=1
                if err_count>=5: 
                    self.error_text = "5 consecutive response errors were received, exiting..."
                    print(self.error_text)
                    self.err =True
                    self.log('Comms Error', 'Multiple Retries')
                    return self.err, rsp
            
            elif rsp[1] != '0':
                #case where error occurs
                #send error command and check error ASTF and proceed accordingly
                msg_err = ['ASTF','K0']
                msg_err_ak = self.ak_convert.build_command(msg_err)
                self.s.sendall(msg_err_ak.encode())
                data = self.s.recv(1024)
                rsp = self.ak_convert.demolish_response(data.decode())
                error_str = self.errors.loc[(self.errors['Code'] == int(rsp[1]),'Error')].item()
                self.error_text = 'The HFID returned the following error :' + error_str + ' The scheduled test will be exited.'
                print(self.error_text)
                err = True
                self.log('HFID Error', error_str)
                return err, rsp

            else:
                send_success = True
                return self.err, rsp

    def HFID_automate(self):
        """Function to automate the 
        """
        # Reset PAG condition indicators to Off
        with self.s:
            self.s.connect((self.HOST, self.PORT))
            #Set Remote 
            self.err, rsp = self.comms_wrapper(['SREM', 'K0'])
            #Check Oven Temp
            if not self.err:
                t_oven = 0
                while t_oven < 180:
                    msg = ['ATEM','K0']
                    self.err, rsp = self.comms_wrapper(msg)
                    t_oven = int(rsp[3])
                    if t_oven < 180:
                        print("Waiting for oven temperature to reach > 180 C before proceeding.")
                        print("    The oven temperature is currently", str(t_oven),"C", end = '\r')
                        time.sleep(1)
                    else:
                        print("The oven temperature is currently " + str(t_oven) +". Proceeding to next step.")
            # Ignite
            if not self.err:
                msg = ['STBY','K0']
                self.err, rsp = self.comms_wrapper(msg) 
                print("Burner ignition process started.")
            #monitor air/fuel pressures
            if not self.err:
                t = 10
                air = []
                fuel = []
                air_pass_condition = [10, 13]
                fuel_pass_condition = [10, 13]
                print("Monitoring air and fuel pressure during startup.")
                #print("Air Pressure,", "Fuel Pressure")
                while t > 0:
                    msg = ['ADRU', 'K0']
                    err, rsp = self.comms_wrapper(msg)
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
                    self.log("Error", "Pressure Failure, Air = " + str(air_avg) + ", Fuel = " + str(fuel_avg))
                    self.err = True               
            # 1 hr warmup
            if not self.err:
                t_remaining = 10 #3600
                t_burner_min = 350
                print("Burner Warmup Started")
                #print("Reading, ", "Time Remaining")
                while t_remaining >= 0:
                    msg = ['ATEM', 'K0']
                    self.err, rsp = self.comms_wrapper(msg)
                    t_burner = int(rsp[4])
                    print('    Burner temperature is', t_burner,'C. Time remaining =',t_remaining,' ', end='\r')
                    time.sleep(1)
                    t_remaining -= 1
                if t_burner > t_burner_min:
                    print("The burner has successfully preheated.                     ")
                else:
                    print("The burner failed to preheat.                       ")
                    self.log("Error", "Burner preheat failure. T_burner =" +str(t_burner))
            # Set Manaul Range mode
            if not self.err:
                self.err, rsp = self.comms_wrapper(['SARA', 'K0']) 
            # Set Range
            if not self.err:
                self.err, rsp = self.comms_wrapper(['SEMB', 'K0', '2']) # confirm range and how to select desired range
                print("The instrument range has been set to 2.")
            # Zero Calibration
            if not self.err:
                t_err =  300
                t = t_err
                readings = []
                complete = False
                stability_criteria = 0.1
                print("Zero Calibration Started")
                #print("Reading:")
                while t > 0 and not complete:
                    msg = ['AKON', 'K0']
                    self.err, rsp = self.comms_wrapper(msg)
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
                            self.err, rsp = self.comms_wrapper(msg2)
                            complete = True
                            print("The instrument was zeroed successfully")
                        else:
                            pass
                    t -= 1
                    time.sleep(1)
                if t == 0:
                    print("The reading failed to stabilize in the alloted time. Exiting..      ")
                    self.log("Error", "Failed to stabilize during zero calibration")
                    self.err = True             
            # span calibration
            if not self.err:
                t_err = 300
                t = t_err
                readings = []
                complete = False
                stability_criteria = 0.1
                print("Span Calibration Started")
                while t > 0 and not complete:
                    msg = ['AKON', 'K0']
                    self.err, rsp = self.comms_wrapper(msg)
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
                            self.err, rsp = self.comms_wrapper(msg)
                            complete = True
                            print("The instrument was spanned successfully    ")                        
                        else:
                            pass
                    t -= 1
                    time.sleep(1)
                if t == 0:
                    print("The reading failed to stabilize in the alloted time. Exiting..     ")
                    self.log("Error", "Failed to stabilize during span calibration")
                    self.err = True
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
                    self.err, rsp = self.comms_wrapper(msg)
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
                                self.log("Test Result", "Successful completion. PAG #1 Air Reading = " + str(average_reading))                                
                                complete = True
                                print("PAG #1 is functioning as expected")
                                # Set PAG 1 indicator to PASS
                            else:
                                self.log("Test Results", "Test Failure. PAG #1 Air Reading = " + str(average_reading))
                                print("PAG #1 is NOT functioning")
                                complete = True
                                # Set PAG 1 indicator to FAIL
                        else:
                            pass
                    t -= 1
                    time.sleep(1)
                if t == 0:
                    print("The reading failed to stabilize in the alloted time.              ")
                    self.log("Error", "PAG #1 Failed to stabilize during reading")
                # Reset solenoid to neutral setting.
            # check PAG 2
            if not self.err:
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
                    self.err, rsp = self.comms_wrapper(msg)
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
                                self.log("Test Result", "Successful completion. PAG #2 Air Reading = " + str(average_reading))                                
                                complete = True
                                print("PAG #2 is functioning as expected")
                                # Set PAG 2 indicator to PASS
                            else:
                                self.log("Test Results", "Test Failure. PAG #2 Air Reading = " + str(average_reading))
                                print("PAG #2 is NOT functioning")
                                complete = True
                                # Set PAG 2 indicator to FAIL
                        else:
                            pass
                    t -= 1
                    time.sleep(1)
                if t == 0:
                    print("The reading failed to stabilize in the alloted time.              ")
                    self.log("Error", "PAG #1 Failed to stabilize during reading")
                # reset solenoid to neutral position
            # Stop Fuel flow (When complete or if error occurs)
            if self.err: # reset error for shutdown comms
                self.err = False
            self.err, rsp = self.comms_wrapper(['SPAU', 'K0'])
            print("Fuel flow to instrument stopped.")
            # Purge analyser for 5 mins
            t_remaining = 15
            msg = ['SSPL', 'K0']
            self.err, rsp = self.comms_wrapper(msg)
            print("Purging instrument with air")
            while t_remaining >= 0:
                msg4 = ['AKON', 'K0']
                self.err, rsp = self.comms_wrapper(msg4)
                reading = rsp[2].replace("'",'')
                print('Reading =', reading, 'Time remaining = ' + str(t_remaining) +" s ", end='\r')
                time.sleep(1)
                t_remaining -= 1
            self.err, rsp = self.comms_wrapper(msg) #check if this also shuts off zero gas. If not set to whatever initial state is
            print("Purging complete                  ")   
            # Return instrument to manual mode
            self.err, rsp = self.comms_wrapper(['SMAN', 'K0'])
            print("Instrument returned to Manual mode. Test completed.")             
