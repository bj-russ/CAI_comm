#!/usr/bin/env python3

import sys
import socket
import selectors
import types
import pandas as pd
import AK_format
from time import sleep

sel = selectors.DefaultSelector()                                   # initiate the selector module (used for parallel use of sockets)

cvs_lookup = pd.read_csv('cvs_lookup.csv')                          # grab data for lookup of responses from test file (note the confusing use of CVS and CSV)

#-----------define functions--------------

#----------------this is used to create a log of send/receives for debugging-------------------

#create new log (replace old)
file = open("log_server.csv","r+")
file.truncate(0)
file.close()

#----------------this is used to track the send/receives for troubleshooting the server.---------------------

def log(cr, var):
    ls = [cr,var]
    df = pd.DataFrame([ls], columns=['In/Out','Message'])
    df.to_csv('log_server.csv', mode='a', header=False)



#----------------this is used to accept new connections and register them.------------------------

def accept_wrapper(sock): 
    conn, addr = sock.accept()                                      # Should be ready to read
    print("accepted connection from", addr)
    conn.setblocking(False)                                         # configure connection to not block the terminal
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")      # configure data as name for non-standard types
    events = selectors.EVENT_READ | selectors.EVENT_WRITE           # define types of events to use with selectors module
    sel.register(conn, events, data=data)                           # register the connection as active on the server


#----------------this is used to service active connections when new messages arrive or there are items in the output buffer----------------

def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)                                 # Read data from socket
        if recv_data:                                               # If there is new data
           data.inb += recv_data
           print("Received ", repr(data.inb), "from ", data.addr)        
                                                            #lookup response and store to buffer.        
           commands_recvb = data.inb.decode()                       # Convert from binary
           data.inb = b''                                           # clear input buffer
           commands_recvb.split()                                   # trim whitespace
           commands_recv = commands_recvb.split('\x03 ')            # create list of individual commands in buff
                                                            #Break down to list of command and parameters
           AK = AK_format.ak_handler()                              # initiate instance of Ak_handler
           commands = []
           for i in commands_recv:   
               commands.append(AK.demolish_command(i))              # demolish ak messages and store in list
           commands=commands[:-1]                                   # drop empty first cell
#---------------------------------------------------------
           response_ls = ak_lookup(commands)                # call subroutine to lookup responses from sample data (this is where the future logic and instrument I/O will be done)
#---------------------------------------------------------
           response_ls_ak =[]                                       # convert responses in list to list of AK formated strings
           for i in response_ls:
               response_ak = AK.build_response(i)
               response_ls_ak.append(response_ak)
           response_ak_comb = ''                                    
           for i in response_ls_ak:                                 # update output buffer with responses
               response_ak_comb += i 
           data.outb = response_ak_comb.encode()

        else:
            print("closing connection to", data.addr)
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:                                # write response case
        if data.outb:                                               # data is waiting to be send to client
            print("Sending ", repr(data.outb), "to ", data.addr)    
            log("Sent to Client",data.outb)                         # add line in server log with data that is send
            sent = sock.send(data.outb)                             # write data
            data.outb = data.outb[sent:]                            # remove written data from buffer
            
def ak_lookup(commands):
    lookup_ls = []                                                  # create list to fill with commands
    for i in commands:
        lookup_str = ''                     
        for n in i:
            lookup_str += n + ' '                                   # combine command and parameter from list of strings into string to be compatible with lookup table
        lookup_str = lookup_str.strip()
        lookup_ls.append(lookup_str)                                # fill list with what to lookup
    response_ls = []                                                # create list to fill with responses
    for i in lookup_ls:
        response_str=''
        response_lookup = cvs_lookup[cvs_lookup.Command == i]                                       #create subset of lookup table for this command only (could be used if we wanted multiple responses)
        log("Received from Client",i)                                                               #add command to server log
        response_str = response_lookup.loc[(response_lookup['Command'] == i,'Response')].item()     #lookup corresponding response string from lookup table
        response_ls.append(response_str.split(' '))                                                 #build list of responses (splits the string for each response into sublist of command and parameters for each response)
    return response_ls


#------Set up connection and start listening----------

#if len(sys.argv) != 3:
#    print("usage:", sys.argv[0], "<host> <port>")
#    sys.exit(1)

#host, port = sys.argv[1], int(sys.argv[2])
#load server address location from config file
host_add = pd.read_csv('hostinfo.cfg', names = ['HOST','PORT'])
host = host_add.iloc[0,0]
port = host_add.iloc[0,1]

lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)       # define socket type. AF_INET = internet address family IPv4, SOCK_STREAM = TCP (Can also use IPv6 and/or UDP)
lsock.bind((host, port))                                        # bind the socket to the IP and Port
lsock.listen()                                                  # set port to listen for incomming connections
print("listening on", (host, port))
lsock.setblocking(False)                                        # set socket to not block (allows multi connections and logic to run in parallel)
sel.register(lsock, selectors.EVENT_READ, data=None)            # register the socket on the server and configure basic selector info.

#-----configure new connections and service active connections as needed------

try: 
    while True:                                                 # loop forever
        events = sel.select(timeout=1)                       # wait for read selector event (EVENT_READ)
        for key, mask in events:                                # access key and mask for use in determining what to do
            if key.data is None:                                # if there is no data, this is a new connection that needs to be accepted.
                accept_wrapper(key.fileobj)
            else:                                               # if there is data, this is an established connected that needs to be serviced.
                service_connection(key, mask)
                sleep(0.01)
                
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()
