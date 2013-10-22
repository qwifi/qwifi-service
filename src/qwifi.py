#!/usr/bin/python
# For checking syslog quickly use in /var/log$ tail -f syslog
import MySQLdb
import threading
import time
import sys, os
import syslog
import daemon.pidlockfile
from collections import namedtuple
import subprocess
import ConfigParser
import argparse

modes = ("DAEMON", "FOREGROUND")
modes = namedtuple("mode", modes)(*range(len(modes)))
mode = modes.DAEMON

logLevels = ("NONE", "ERROR", "WARNING", "INFO", "DEBUG")  # to add a new mode we just need another tuple entry
# create class logLevels with attributes that are members of logLevels tuple
logLevels = namedtuple("logLevels", logLevels)(*range(len(logLevels)))
logLevel = logLevels.WARNING

Config = ConfigParser.ConfigParser()

# Helper function for ConfigParser
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

# variables from qwifi.conf
server = ""
user = ""
password = ""
database = ""
logging = ""

# set global configuration variables from configuration file
def parseConfigFile(path):
    global server
    global user
    global password
    global database
    global logLevel

    Config.read(path)

    try:
        server = ConfigSectionMap("database")['server']
        user = ConfigSectionMap("database")['username']
        password = ConfigSectionMap("database")['password']
        database = ConfigSectionMap("database")['database']
        logLevel = logLevels._asdict()[ConfigSectionMap("logging")['level'].upper()]
    except ConfigParser.NoSectionError:
        print "User Error", "File does NOT exist or file path NOT valid."
        sys.exit(1)

def dropConnection(macAddr):
    log("dropConnection", "Mac Address %s is being dropped." % macAddr, logLevels.DEBUG)
    subprocess.call(["sudo", "hostapd_cli", "disassociate", macAddr])

def error(tag, e):
    try:
        log(tag, "MySQL Error [%d]: %s" % (e.args[0], e.args[1]), logLevels.ERROR)
    except IndexError:
        log(tag, "MySQL Error: %s" % str(e), logLevels.ERROR)

def updateRadcheck(dataBase, cursor):
    try:
        cursor.execute("INSERT INTO radcheck (username, attribute, op, value) SELECT radcheck.username, 'Auth-Type', ':=', 'Reject' FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.attribute='Session-Timeout' AND TIMESTAMPDIFF(SECOND, radacct.acctstarttime, NOW()) > radcheck.value AND radacct.acctstoptime is NULL;")
        if int(cursor.rowcount) > 0:
            log("updateRadcheck", "we have updated radcheck", logLevels.DEBUG)
        dataBase.commit()
    except MySQLdb.Error, e:
        error("updateRadcheck", e)
        dataBase.rollback()
        sys.exit()

def disassociate(cursor):
    cursor.execute("SELECT radacct.callingstationId FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.value = 'Reject' AND radacct.acctstoptime is NULL;")
    mac_addresses = set(cursor.fetchall())
    for macAddr in mac_addresses:
        log("dissassociate", "dropping %s" % macAddr, logLevels.DEBUG)
        threading.Thread(target=dropConnection(macAddr[0].replace('-', ':')))

def cull(dataBase, cursor):
    try:
        cursor.execute("SELECT username FROM radcheck WHERE value = 'Reject';")
        users_culled = cursor.fetchall()
        for user in users_culled:
            log("cull", "Taking out %s user from radcheck." % user, logLevels.DEBUG)
        cursor.execute("DELETE FROM radcheck WHERE username IN (SELECT username FROM (SELECT username FROM radcheck WHERE value='Reject') temp);")
        if int(cursor.rowcount) > 0:
            log("cull", "We have deleted %s things from radcheck" % cursor.rowcount, logLevels.DEBUG)
        dataBase.commit()
    except MySQLdb.Error, e:
        error("cull", e)
        dataBase.rollback()

# A general log function, the modes are normal, Error, Warning, Debug
def log(tag, message, level):
    if mode == modes.FOREGROUND:
        print "<" + tag + ">" + message
    if level != logLevels.NONE and level <= logLevel:
        if level == logLevels.ERROR:
            syslog.syslog(syslog.LOG_ERR, "<" + tag + ">" + message)
        elif level == logLevels.WARNING:
            syslog.syslog(syslog.LOG_WARNING, "<" + tag + ">" + message)
        elif level == logLevels.INFO:
            syslog.syslog(syslog.LOG_INFO, "<" + tag + ">" + message)
        elif level == logLevels.DEBUG:
            syslog.syslog(syslog.LOG_DEBUG, "<" + tag + ">" + message)
        else:
            syslog.syslog("<UNKNOWN MODE>" + message)

def main():
    global server
    global user
    global password
    global database

    log('main', 'Started logging process on daemon', logLevels.DEBUG)

    while True:
        try:
            db = MySQLdb.connect(server, user, password, database)
        except MySQLdb.Error, e:
            error("main", e)
            raise
        try:
            cursor = db.cursor()
        except e:
            print "blah."
            log("main", e, logLevels.ERROR)
            sys.exit()

    # print "We have opened MySQLdb successfully!"

        updateRadcheck(db, cursor)  # update radcheck with reject for old sessions
        disassociate(cursor)  # kick off all of the old sessions
        cull(db, cursor)  # remove unneccassery data from DB
        time.sleep(5)  # loop every 5 seconds

# parsing through the command line arguments.
parser = argparse.ArgumentParser()
parser.add_argument("-n", action="store_true", help="Displays messages to the foreground(stdout) or syslog.")
parser.add_argument("-c", default="qwifi.conf", help="allows you to designate where qwifi.conf is located.")
args = parser.parse_args()

if __name__ == '__main__':
  if not os.path.exists("/var/run/qwifi.pid.lock"):
    if args.n == True:
        mode = modes.FOREGROUND
        logLevel = logLevels.DEBUG
        parseConfigFile(args.c)
        main()
    else:
        parseConfigFile(args.c)
        with daemon.DaemonContext(working_directory='.', pidfile=daemon.pidlockfile.PIDLockFile("/var/run/qwifi.pid"), stderr=sys.stderr):
            main()
  else:
    print "Service is already running."
