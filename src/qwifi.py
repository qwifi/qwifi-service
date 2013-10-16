#!/usr/bin/python
#For checking syslog quickly use in /var/log$ tail -f syslog
import MySQLdb
import threading
import time
import sys
import syslog
import daemon
import lockfile
from collections import namedtuple
import subprocess
import ConfigParser

modes = ("SYSLOG","FOREGROUND")#to add a new mode we just need another tuple entry
#create class modes with attributes that are members of modes tuple
modes = namedtuple("modes", modes)(*range(len(modes)))

logMode = modes.SYSLOG

#Reading in default information from qwifi.ini
Config = ConfigParser.ConfigParser()

def ConfigDbPath(path):
  global Config
  if path != "":
      Config.read("%sqwifi.ini" %path)
      print "%sqwifi.ini" %path
      Config.sections()
  else:
    Config.read("qwifi.ini")
    Config.sections()

#Helper function for ConfigParser
def ConfigSectionMap(section):
  dict1 = {}
  options = Config.options(section)
  for option in options:
    try:
      dict1[option] = Config.get(section, option)
      if dict1[option] == -1:
        print("skiping: %s" % option)
    except:
      print("exception on %s!" % option)
      dict1[option] = NONE
  return dict1

#variables from qwifi.ini
server = ""
user = ""
password = ""
table = ""
logging = ""

#setting the global variables for the database variables
def SetDbVar():
  global server
  global user 
  global password 
  global table 
  global logging 

  try: 
    server  = ConfigSectionMap("Database")['server']
    user = ConfigSectionMap("Database")['username']
    password = ConfigSectionMap("Database")['password']
    table = ConfigSectionMap("Database")['table'] 
    logging = ConfigSectionMap("Options")['logging']
  except ConfigParser.NoSectionError, e:
    logError("User Error", "File does NOT exist or does NOT contain a valid section.")
    sys.exit()

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
            log("cull","We have deleted %s things from radcheck" %cursor.rowcount)
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
        syslog.syslog(syslog.LOG_ERR, "<" + tag + ">" + message)   

def main(): 
  global server
  global user
  global password
  global table
 
  while True:
    try:
        #db = MySQLdb.connect("localhost","root","password","radius")
        db = MySQLdb.connect(server,user,password,table)
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
        ConfigDbPath("")
        SetDbVar()
        main()
    elif sys.argv[1] == '-c':
      try:
        ConfigDbPath(sys.argv[2])
      except IndexError, e:
        logError("User Error", "I need a path to qwifi.ini that is valid.")
        sys.exit()
      SetDbVar()
      main()
else:
    with daemon.DaemonContext(working_directory = '.', pidfile=lockfile.FileLock("/var/run/qwifi.pid")):
        main()
