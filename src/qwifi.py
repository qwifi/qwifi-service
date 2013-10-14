#!/usr/bin/python
import MySQLdb
import threading
import time
import sys
import syslog
from daemon import DaemonContext
from collections import namedtuple
import subprocess

modes = ("SYSLOG","FOREGROUND")#to add a new mode we just need another tuple entry
#create class modes with attributes that are members of modes tuple
modes = namedtuple("modes", modes)(*range(len(modes)))

logMode = modes.SYSLOG

def dropConnection(macAddr):
  log("dropConnection", "Mac Address %s is being dropped." %macAddr)
  subprocess.call(["sudo", "hostapd_cli", "disassociate", macAddr])

def error(tag, e):
    try:
        logError(tag, "MySQL Error [%d]: %s" % (e.args[0], e.args[1]) )
    except IndexError:
        logError(tag,"MySQL Error: %s" % str(e))
        
def updateRadcheck(dataBase, cursor):
    try:
        cursor.execute("INSERT INTO radcheck (username, attribute, op, value) SELECT radcheck.username, 'Auth-Type', ':=', 'Reject' FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.attribute='Session-Timeout' AND TIMESTAMPDIFF(SECOND, radacct.acctstarttime, NOW()) > radcheck.value AND radacct.acctstoptime is NULL;")
        if int(cursor.rowcount) > 0:
            log("updateRadcheck", "we have updated radcheck")
        dataBase.commit()    
    except MySQLdb.Error, e:
        error("updateRadcheck", e)
        dataBase.rollback()

def disassociate(cursor):
    cursor.execute("SELECT radacct.callingstationId FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.value = 'Reject' AND radacct.acctstoptime is NULL;")
    mac_addresses = set(cursor.fetchall())
    for macAddr in mac_addresses:
        log("dissassociate", "dropping %s" % macAddr)
        threading.Thread(target=dropConnection(macAddr[0].replace('-', ':')))

def cull(dataBase, cursor):
    try:
        cursor.execute("SELECT username FROM radcheck WHERE value = 'Reject';")
        users_culled = cursor.fetchall()
        for user in users_culled:
            log("cull","Taking out %s user from radcheck." %user)
        cursor.execute("DELETE FROM radcheck WHERE username IN (SELECT username FROM (SELECT username FROM radcheck WHERE value='Reject') temp);")
        if int(cursor.rowcount) > 0:
            log("cull","We have deleted %s number of things from radcheck" %cursor.rowcount)
        dataBase.commit()
    except MySQLdb.Error, e:
        error("cull",e)
        dataBase.rollback()

def log(tag, message):
    global logMode
    if logMode == modes.FOREGROUND:
        print("<" + tag + ">" + message)
    elif logMode == modes.SYSLOG:
        syslog.syslog("<" + tag + ">" + message)

def logError(tag, message):
    global logMode
    if logMode == modes.FOREGROUND:
        print("<" + tag + ">" + message)
    elif logMode == modes.SYSLOG:
        syslog.syslog(syslog.ERR, "<" + tag + ">" + message)   

def main():  
  while True:
    try:
        db = MySQLdb.connect("localhost","root","password","radius")
        cursor = db.cursor()
        syslog.syslog("Started logging process on daemon.")
    except MySQLdb.Error, e:
        error("main", e)

    updateRadcheck(db, cursor)#update radcheck with reject for old sessions
    disassociate(cursor)#kick off all of the old sessions
    cull(db, cursor)#remove unneccassery data from DB
    time.sleep(5) #loop every 5 seconds

if len(sys.argv) > 1:
    if sys.argv[1] == "-n":
        logMode = modes.FOREGROUND
        main()
else:
    with DaemonContext(working_directory = '.'):
        main()