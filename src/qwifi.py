#!/usr/bin/python
import MySQLdb
import threading
import time
import sys
import syslog
from daemon import DaemonContext
import subprocess

bool log = true

def dropConnection(macAddr):
  #print "Mac Address " + macAddr #for testing
  syslog.syslog("Mac Address %s is being dropped." %macAddr)
  subprocess.call(["sudo", "hostapd_cli", "disassociate", macAddr])

def printError(e):
    try:
        print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
        syslog.syslog(syslog.LOG_ERR, "Unable to open the database")
    except IndexError:
        print "MySQL Error: %s" % str(e)
        syslog.syslog(syslog.LOG_ERR, "Unable to open the database, perhaps wrong values passed in?")


def updateRadcheck(dataBase, cursor):
    try:
        cursor.execute("INSERT INTO radcheck (username, attribute, op, value) SELECT radcheck.username, 'Auth-Type', ':=', 'Reject' FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.attribute='Session-Timeout' AND TIMESTAMPDIFF(SECOND, radacct.acctstarttime, NOW()) > radcheck.value AND radacct.acctstoptime is NULL;")
        if int(cursor.rowcount) > 0:
          syslog.syslog("We have updated something into radcheck")
        dataBase.commit()    
        print "updated radcheck"
    except MySQLdb.Error, e:
        printError(e)
        dataBase.rollback()
        print("Error updating radcheck")
        syslog.syslog(syslog.ERR, "Error updating radcheck table.")

def disassociate(cursor):
    cursor.execute("SELECT radacct.callingstationId FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.value = 'Reject' AND radacct.acctstoptime is NULL;")
    mac_addresses = set(cursor.fetchall())
    for macAddr in mac_addresses:
        threading.Thread(target=dropConnection(macAddr[0].replace('-', ':')))

def cull(dataBase, cursor):
    try:
        if log == true:
          cursor.execute("SELECT username FROM radcheck WHERE value = 'Reject';")
          users_culled = cursor.fetchall()
          for user in users_culled:
            #print "Taking out %s user from radcheck." %user
            syslog.syslog("Taking out %s user from radcheck." %user)

        cursor.execute("DELETE FROM radcheck WHERE username IN (SELECT username FROM (SELECT username FROM radcheck WHERE value='Reject') temp);")
        if int(cursor.rowcount) > 0:
          syslog.syslog("We have deleted %s number of things from radcheck" %cursor.rowcount)
        dataBase.commit()
        print "Cleaned up radcheck"
    except MySQLdb.Error, e:
        printError(e)
        dataBase.rollback()
        print("Error cleaning up radcheck")
        syslog.syslog(syslog.ERR, "Error cleaning up radcheck")


def main():
  while True:
    print "loop entry"
    try:
        #db = MySQLdb.connect("localhost","root","password","radius")
        db = MySQLdb.connect("localhost", "test", "test123", "radius")
        cursor = db.cursor()
        syslog.syslog("Started logging process on daemon.")
    except MySQLdb.Error, e:
        printError(e)

    updateRadcheck(db, cursor)#update radcheck with reject for old sessions
    disassociate(cursor)#kick off all of the old sessions
    cull(db, cursor)#remove unneccassery data from DB
    time.sleep(5) #loop every 5 seconds

#the stdout/stderror part is for testing
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
