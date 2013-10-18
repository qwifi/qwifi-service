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
import argparse

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
      #print "%sqwifi.ini" %path
      Config.sections()
  else:
    Config.read("qwifi.ini")
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
      dictionary[option] = NONE
  return dictionary

#variables from qwifi.ini
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
  except ConfigParser.NoSectionError, e:
    log("User Error", "File does NOT exist or file path NOT valid.", 2)
    sys.exit()

def dropConnection(macAddr):
  log("dropConnection", "Mac Address %s is being dropped." %macAddr, 4)
  subprocess.call(["sudo", "hostapd_cli", "disassociate", macAddr])

def error(tag, e):
    try:
        log(tag, "MySQL Error [%d]: %s" % (e.args[0], e.args[1]), 2)
    except IndexError:
        log(tag,"MySQL Error: %s" % str(e), 2)
        
def updateRadcheck(dataBase, cursor):
    try:
        cursor.execute("INSERT INTO radcheck (username, attribute, op, value) SELECT radcheck.username, 'Auth-Type', ':=', 'Reject' FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.attribute='Session-Timeout' AND TIMESTAMPDIFF(SECOND, radacct.acctstarttime, NOW()) > radcheck.value AND radacct.acctstoptime is NULL;")
        if int(cursor.rowcount) > 0:
            log("updateRadcheck", "we have updated radcheck", 4)
        dataBase.commit()    
    except MySQLdb.Error, e:
        error("updateRadcheck", e)
        dataBase.rollback()
        sys.exit()

def disassociate(cursor):
    cursor.execute("SELECT radacct.callingstationId FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.value = 'Reject' AND radacct.acctstoptime is NULL;")
    mac_addresses = set(cursor.fetchall())
    for macAddr in mac_addresses:
        log("dissassociate", "dropping %s" % macAddr, 4)
        threading.Thread(target=dropConnection(macAddr[0].replace('-', ':')))

def cull(dataBase, cursor):
    try:
        cursor.execute("SELECT username FROM radcheck WHERE value = 'Reject';")
        users_culled = cursor.fetchall()
        for user in users_culled:
            log("cull","Taking out %s user from radcheck." %user, 4)
        cursor.execute("DELETE FROM radcheck WHERE username IN (SELECT username FROM (SELECT username FROM radcheck WHERE value='Reject') temp);")
        if int(cursor.rowcount) > 0:
            log("cull","We have deleted %s things from radcheck" %cursor.rowcount, 4)
        dataBase.commit()
    except MySQLdb.Error, e:
        error("cull",e)
        dataBase.rollback() 

#A general log function, the modes are 1 = normal, 2 = Error, 3 = Warning, 4 = Debug
def log(tag, message, mode):
    global logMode
    
    if logMode == modes.FOREGROUND:
      print ("<" + tag + ">" + message)
    else:
      if mode == 1:
        syslog.syslog("<" + tag + ">" + message)
      elif mode == 2:
        syslog.syslog(syslog.LOG_ERR, "<" + tag + ">" + message)
      elif mode == 3:
        syslog.syslog(syslog.LOG_WARNING, "<" + tag + ">" + message)
      elif mode == 4:
        syslog.syslog(syslog.LOG_DEBUG, "<" + tag + ">" + message)
      else:
        syslog.syslog("<UNKNOWN MODE>" + message)

def main(): 
  global server
  global user
  global password
  global database

  log('main','Started logging process on daemon', 4)
 
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
        log("main", e, 2)
        sys.exit()

    #print "We have opened MySQLdb successfully!"

    updateRadcheck(db, cursor)#update radcheck with reject for old sessions
    disassociate(cursor)#kick off all of the old sessions
    cull(db, cursor)#remove unneccassery data from DB
    time.sleep(5) #loop every 5 seconds

#parsing through the command line arguments.
parser = argparse.ArgumentParser()
parser.add_argument("-n", action = "store_true", help="Displays messages to the foreground(stdout) or syslog.")
parser.add_argument("-c", default = "", help = "allows you to designate where qwifi.ini is located.")
args = parser.parse_args()

if args.n == True:
  logMode = modes.FOREGROUND
  ConfigDbPath(args.c)
  SetDbVar()
  main()
else:
  ConfigDbPath(args.c)
  SetDbVar()
  with daemon.DaemonContext(working_directory = '.', pidfile=lockfile.FileLock("/var/#run/qwifi.pid")): 
    main()
