#!/usr/bin/python
import MySQLdb
import threading
import time
import sys
from daemon import DaemonContext
import subprocess

def dropConnection(macAddr):
  print "Mac Address " + macAddr[0] #for testing
  subprocess.call(["sudo", "hostapd_cli", "disassociate", macAddr[0]])

def main():
  while True:
    print "loop entry"
    db = MySQLdb.connect("localhost","root","password","radius")
    cursor = db.cursor()
    cursor.execute("INSERT INTO radcheck (username, attribute, op, value) SELECT radcheck.username, 'Auth-Type', ':=', 'Reject' FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.attribute='Session-Timeout' AND TIMESTAMPDIFF(SECOND, radacct.acctstarttime, NOW()) > radcheck.value AND radacct.acctstoptime is NULL;")

    cursor.execute("SELECT radacct.callingstationId FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.value = 'Reject' AND radacct.acctstoptime is NULL;")
    mac_addresses = list(set(cursor.fetchall()))
    for macAddr in mac_addresses:
      threading.Thread(target=dropConnection(macAddr))
    
    cursor.execute("SELECT username FROM radius.radcheck WHERE value = \'Reject\';")
    rows = cursor.fetchall()

    if rows:
      for row in rows:
        print "row " + row[0] #testing
        cursor.execute("DELETE FROM radius.radcheck WHERE username = '%s';" % row)

    db.commit()
    time.sleep(5) #loop every 5 seconds

#the stdout part is for testing
with DaemonContext(working_directory = '.', stdout=sys.stdout):
  main()


###FUTURE ADAPTATIONS###
 #if (the number of connections to kill) >= 100:
 #   fire off 100 dropConnection threads
 #   wait for them to finish
 #   fire off 100 more... etc etc

 #Logging of DB changes and qwifi-service operations

 #Anything else we find
