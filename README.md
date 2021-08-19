# PAG_varifier
Automatic verification of the PAG system using a CAI HFID instrument with AK commands

The PAG_supervisor.py progrom will read the host, port info and the sheduled time for the test from the config.csv file and execute testing the PAG air at that time.

The PAG_log.csv is used to keep track of errors and the measured ppm of each PAG unit during a test.

Solenoid control hardware will need to be added to select the PAG units individually during testing.

The AK-server.py, cvs_lookup.csv and hostinfo.cfg are used to simulate the HFID responses for testing purposes.

Currently the times during the sequence are shortened for testing efficiency.

To run in Demo Mode, run AK-server.py first to initiate the ip adress to write to...