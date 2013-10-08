#!/usr/bin/python
import MySQLdb
import threading
import time
import sys
from daemon import DaemonContext
import subprocess

def dropConnection(macAddr):
  print "Mac Address " + macAddr #for testing
  subprocess.call(["sudo", "hostapd_cli", "disassociate", macAddr])

def main():
  while True:
    print "loop entry"
    db = MySQLdb.connect("localhost","root","password","radius")
    cursor = db.cursor()

    try:
        cursor.execute("INSERT INTO radcheck (username, attribute, op, value) SELECT radcheck.username, 'Auth-Type', ':=', 'Reject' FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.attribute='Session-Timeout' AND TIMESTAMPDIFF(SECOND, radacct.acctstarttime, NOW()) > radcheck.value AND radacct.acctstoptime is NULL;")
        db.commit()    
        print "updated radcheck"
    except:
        db.rollback()
        print("Error updating radcheck")

    cursor.execute("SELECT radacct.callingstationId FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.value = 'Reject' AND radacct.acctstoptime is NULL;")
    mac_addresses = set(cursor.fetchall())
    for macAddr in mac_addresses:
      threading.Thread(target=dropConnection(macAddr[0].replace('-', ':')))
    
    try:
        cursor.execute("DELETE FROM radcheck WHERE username IN (SELECT username FROM (SELECT username FROM radcheck WHERE value='Reject') temp);")
        db.commit()
        print "Cleaned up radcheck"
    except:
        db.rollback()
        print("Error cleaning up radcheck")

    time.sleep(5) #loop every 5 seconds

#the stdout part is for testing
with DaemonContext(working_directory = '.', stdout=sys.stdout, stderr=sys.stderr):
  main()


###FUTURE ADAPTATIONS###
#def subsets(l, n):
    #for i in xrange(0, len(l), n):
        #yield l[i:i+n]

#if len(macAddr) >= 100:
#  for subset in subsets(mac_addresses, 100):
#    threads = []
#    for macAddr in subset:
#      t = threading.Thread(target=dropConnection(macAddr))
#      threads.append(t)
#    [i.join() for i in threads]#wait for each thread to finish
#else:
#  for macAddr in mac_addresses:
#    threading.Thread(target=dropConnection(macAddr))
