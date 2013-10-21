#!/usr/bin/python
#For checking syslog quickly use in /var/log$ tail -f syslog
import MySQLdb
import threading
import time
import sys, os
import syslog
import daemon
import daemon.pidlockfile
from collections import namedtuple
import subprocess
import ConfigParser
import argparse

modes = ("SYSLOG","FOREGROUND", "NORMAL", "ERROR", "WARNING", "DEBUG")#to add a new mode we just need another tuple entry
#create class modes with attributes that are members of modes tuple
modes = namedtuple("modes", modes)(*range(len(modes)))

logMode = modes.SYSLOG

#Reading in default information from qwifi.conf
Config = ConfigParser.ConfigParser()

def ConfigDbPath(path):
  global Config
  if path != "":
      Config.read("%sqwifi.conf" %path)
      #print "%sqwifi.conf" %path
      Config.sections()
  else:
    Config.read("qwifi.conf")
    Config.sections()

#Helper function for ConfigParser
def ConfigSectionMap(section):
  dictionary = {}
  options = Config.options(section)
  for option in options:
    try:
      dictionary[option] = Config.get(section, option)
      if dictionary[option] == -1:
        print("skiping: %s" % option)
    except:
      print("exception on %s!" % option)
      dictionary[option] = None
  return dictionary

#variables from qwifi.conf
server = ""
user = ""
password = ""
database = ""
logging = ""

#setting the global variables for the database variables
def SetDbVar():
  global server
  global user 
  global password 
  global database 
  global logging 

  try: 
    server  = ConfigSectionMap("Database")['server']
    user = ConfigSectionMap("Database")['username']
    password = ConfigSectionMap("Database")['password']
    database = ConfigSectionMap("Database")['database'] 
    logging = ConfigSectionMap("Options")['logging']
  except ConfigParser.NoSectionError:
    log("User Error", "File does NOT exist or file path NOT valid.", modes.ERROR)
    sys.exit()

def dropConnection(macAddr):
  log("dropConnection", "Mac Address %s is being dropped." %macAddr, modes.DEBUG)
  subprocess.call(["sudo", "hostapd_cli", "disassociate", macAddr])

def error(tag, e):
    try:
        log(tag, "MySQL Error [%d]: %s" % (e.args[0], e.args[1]), modes.ERROR)
    except IndexError:
        log(tag,"MySQL Error: %s" % str(e), modes.ERROR)
        
def updateRadcheck(dataBase, cursor):
    try:
        cursor.execute("INSERT INTO radcheck (username, attribute, op, value) SELECT radcheck.username, 'Auth-Type', ':=', 'Reject' FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.attribute='Session-Timeout' AND TIMESTAMPDIFF(SECOND, radacct.acctstarttime, NOW()) > radcheck.value AND radacct.acctstoptime is NULL;")
        if int(cursor.rowcount) > 0:
            log("updateRadcheck", "we have updated radcheck", modes.DEBUG)
        dataBase.commit()    
    except MySQLdb.Error, e:
        error("updateRadcheck", e)
        dataBase.rollback()
        sys.exit()

def disassociate(cursor):
    cursor.execute("SELECT radacct.callingstationId FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.value = 'Reject' AND radacct.acctstoptime is NULL;")
    mac_addresses = set(cursor.fetchall())
    for macAddr in mac_addresses:
        log("dissassociate", "dropping %s" % macAddr, modes.DEBUG)
        threading.Thread(target=dropConnection(macAddr[0].replace('-', ':')))

def cull(dataBase, cursor):
    try:
        cursor.execute("SELECT username FROM radcheck WHERE value = 'Reject';")
        users_culled = cursor.fetchall()
        for user in users_culled:
            log("cull","Taking out %s user from radcheck." %user, modes.DEBUG)
        cursor.execute("DELETE FROM radcheck WHERE username IN (SELECT username FROM (SELECT username FROM radcheck WHERE value='Reject') temp);")
        if int(cursor.rowcount) > 0:
            log("cull","We have deleted %s things from radcheck" %cursor.rowcount, modes.DEBUG)
        dataBase.commit()
    except MySQLdb.Error, e:
        error("cull",e)
        dataBase.rollback() 

#A general log function, the modes are normal, Error, Warning, Debug
def log(tag, message, mode):
    global logMode
    
    if logMode == modes.FOREGROUND:
      print ("<" + tag + ">" + message)
    else:
      if mode == modes.NORMAL:
        syslog.syslog("<" + tag + ">" + message)
      elif mode == modes.ERROR:
        syslog.syslog(syslog.LOG_ERR, "<" + tag + ">" + message)
      elif mode == modes.WARNING:
        syslog.syslog(syslog.LOG_WARNING, "<" + tag + ">" + message)
      elif mode == modes.DEBUG:
        syslog.syslog(syslog.LOG_DEBUG, "<" + tag + ">" + message)
      else:
        syslog.syslog("<UNKNOWN MODE>" + message)

def main(): 
  global server
  global user
  global password
  global database

  log('main','Started logging process on daemon', modes.DEBUG)
 
  while True:
    try:
        #db = MySQLdb.connect("localhost","root","password","radius")
        db = MySQLdb.connect(server,user,password,database)
    except MySQLdb.Error, e:
        error("main", e)
        sys.exit()
    try:
        cursor = db.cursor()
    except e:
        print "blah."
        log("main", e, modes.ERROR)
        sys.exit()

    #print "We have opened MySQLdb successfully!"

    updateRadcheck(db, cursor)#update radcheck with reject for old sessions
    disassociate(cursor)#kick off all of the old sessions
    cull(db, cursor)#remove unneccassery data from DB
    time.sleep(5) #loop every 5 seconds

#parsing through the command line arguments.
parser = argparse.ArgumentParser()
parser.add_argument("-n", action = "store_true", help="Displays messages to the foreground(stdout) or syslog.")
parser.add_argument("-c", default = "", help = "allows you to designate where qwifi.conf is located.")
args = parser.parse_args()

if not os.path.exists("/var/run/qwifi.pid.lock"):
  if args.n == True:
    logMode = modes.FOREGROUND
    ConfigDbPath(args.c)
    SetDbVar()
    main()
  else:
    ConfigDbPath(args.c)
    SetDbVar()
    with daemon.DaemonContext(working_directory = '.', pidfile=daemon.pidlockfile.PIDLockFile("/var/run/qwifi.pid"), stderr=sys.stderr): 
      main()
else:
  print "Service is already running."
