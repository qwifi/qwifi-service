#CB : This is the python version of the qrencoder and random stuff.
from qrencode import Encoder
import daemon

enc = Encoder()

user_info = {"user"     : "Bob",
             "password" : "Blue",
             "ssid"     : "network_name",
             "time"     : "#_of_minutes" }

im = enc.encode('http://www.gamefaqs.com', {'width':100})
im.save('out.png')

print("{0};{1};{2};{3};".format(user_info["user"], 
                                user_info["password"],
                                user_info["ssid"], 
                                user_info["time"]))
