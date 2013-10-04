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
	  #query number 1 (update db to represent sessions that should be disassociated)
    # So this is the query that inserts a new row into radcheck for the connections that
    # have timed out. Useful for the username field.
    cursor.execute("INSERT INTO radcheck (username, attribute, op, value) SELECT radcheck.username, 'Auth-Type', ':=', 'Reject' FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.attribute='Session-Timeout' AND TIMESTAMPDIFF(SECOND, radacct.acctstarttime, NOW()) > radcheck.value AND radacct.acctstoptime is NULL;")

	
	#list = query number 2 (get list of outdated connections)
  # This set of querys will give us all the mac addresses that need to be dissassociated.
  cursor.execute("SELECT radacct.callingstationId FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.value = 'Reject' AND radacct.acctstoptime is NULL;")
  mac_addresses = cursor.fetchall()
	#for connection in list:
  sudo hostapd_cli disassociate <MACaddr>
		#self = threading.Thread(target=f)
	
	  #query number 3 (clean out the radcheck table)
    cursor.execute("SELECT username FROM radius.radcheck WHERE value = 'Reject';")
    rows = cursor.fetchall();

    # if the data is good we did find connections that should be deleted, else we did not.
    if data:
      count = len(rows)
      for rows in range(0, count)
        data = rows[row]
        #This line below is not working for me.
        cursor.execute("DELETE FROM radius.radcheck WHERE username = '%s';" % data)
    else:


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
