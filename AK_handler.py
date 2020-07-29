

#this class deals with splitting the direct AK commands/responses into a list of elements from the command.
#It will also build AK commands to be sent across the network. Note that responses contain error info in bit 8.
#This should be included in the response list as item 2.

class ak_handler:

    def __init__(self):
        self.stx = '\x02'
        self.etx = '\x03'
        self.sp = ' '    
#construct AK command message from command/parameter list
    def build_command(self, command):
        command_ak = ''
        for i in command:
            command_ak += str(i) + self.sp
        command_ak = self.stx + self.sp + command_ak + self.etx + self.sp
        return command_ak
#construct AK response message from command/parameter list and error
    def build_response(self, response):
        response_ak = ''
        for i in response:
            response_ak += str(i) + self.sp          
        response_ak = self.stx + self.sp + response_ak + self.etx + self.sp
        return response_ak
#demolish AK command to command and parameter
    def demolish_command(self, command_ak):
        str_set = command_ak.split(' ')
        str_reduced = str_set[1:-1]
        return str_reduced
#demolish AK response to command parameter and error
    def demolish_response(self, response_ak): #need to add splitting of error
        str_set = response_ak.split(' ')
        str_reduced = str_set[1:-2]
        return str_reduced


#-----------object testing--------------------

#ak_command = ak_handler()
#command = ['AMDT', 'K0']
#test_c = ak_command.build_command(command)
#print(test_c)
#response = ['AMDT','0', '0.06952', '98.65', '296.35', '0.35', '0', '0', '0', '0.06952', '0.00185', '24.567']
#test_r = ak_command.build_response(response)
#test_d = ak_command.demolish_response(test_r)
#test_dc = ak_command.demolish_command(test_c)
#test='\x02 AMDT K0 \x03'
#test_dc = ak_command.demolish_command(test)
#print(test, test_dc, test_d)
