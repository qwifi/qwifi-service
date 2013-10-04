#This is just stubs right now. I'm pushing it to keep us on the same page.

import MySQLdb
import threading
import time
import os
import daemon

def dropConnection:
	#send command to system to drop connection
	

def main:
	while True:
	#query number 1 (update db to represent sessions that should be disasociated)

	
	#list = query number 2 (get list of outdated connections)
	#for connection in list:
		#self = threading.Thread(target=f)
	
	#query number 3 (clean out the radcheck table)
	time.sleep(5) #loop every 5 seconds

with daemon.DaemonContext(working_directory = '.'):
	main()


###FUTURE ADAPTATIONS###
 #if (the number of connections to kill) >= 100:
 #   fire off 100 dropConnection threads
 #   wait for them to finish
 #   fire off 100 more... etc etc

 #Logging of DB changes and qwifi-service operations

 #Anything else we find