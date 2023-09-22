import random
import string
import uuid
from datetime import datetime
from json import dumps

def makeRunMessage():
    message= {}

    Dstats= {}
    
    dfs= {}
    Dstats['name']= ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=5)) 
    Dstats['absTime']= 25
    Dstats['U_absTime']= "int"
    Dstats['percentageTime']= 0.25
    Dstats['U_percentageTime']= "percent"
    Dstats['priority']= 50
    Dstats['U_prioty']= "int"
    Dstats['idleTime']= 250
    Dstats['U_idleTime']= "int"
    Dstats['resourceUsage']= .5
    Dstats['U_resourceUsage']= "percent"
    # Dstats.append(chunk)
    
    message['name']= "FreeRTOS_RuntimeStats*****"
    message['id']= str(uuid.uuid4())
    message['ts']= str(datetime.now())
    # Dstats.append(general)
    message['datafields']= Dstats
    
    return message


    
#output json
# f = open("sentMessage.json", "w")
# f.write(dumps(makeRunMessage(), indent = 4, default=lambda o: o.__dict__))
# f.close()