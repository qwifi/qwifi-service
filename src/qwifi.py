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
import random
import string

modes = ("DAEMON", "FOREGROUND")
modes = namedtuple("mode", modes)(*range(len(modes)))
mode = modes.DAEMON

logLevels = ("NONE", "ERROR", "WARNING", "INFO", "DEBUG")  # to add a new mode we just need another tuple entry
# create class logLevels with attributes that are members of logLevels tuple
logLevels = namedtuple("logLevels", logLevels)(*range(len(logLevels)))
logLevel = logLevels.WARNING

sessionModes = ("DEVICE", "AP")
sessionModes = namedtuple("sessionModes", sessionModes)(*range(len(sessionModes)))
sessionMode = ""

Config = ConfigParser.ConfigParser()
config_time_stamp = ""
# Helper function for ConfigParser
def config_section_map(section):
    dictionary = {}
    options = Config.options(section)
    for option in options:
        try:
            dictionary[option] = Config.get(section, option)
            if dictionary[option] == -1:
                print("skipping: %s" % option)
        except:
            print("exception on %s!" % option)
            dictionary[option] = None
    return dictionary

# variables from qwifi.conf
server = ""
user = ""
password = ""
database = ""

# set global configuration variables from configuration file
def parse_config_file(path):
    global server
    global user
    global password
    global database
    global logLevel
    global sessionMode
    global config_time_stamp
    config_time_stamp = os.path.getmtime(path)
    Config.read(path)

    try:
        server = config_section_map("database")['server']
        user = config_section_map("database")['username']
        password = config_section_map("database")['password']
        database = config_section_map("database")['database']
        logLevel = logLevels._asdict()[config_section_map("logging")['level'].upper()]
        sessionMode = sessionModes._asdict()[config_section_map("session")['mode'].upper()]
    except ConfigParser.NoSectionError:
        print "User Error", "File does NOT exist or file path NOT valid."
        sys.exit(1)

def drop_connection(macAddr):
    drop_return = subprocess.call(["sudo", "hostapd_cli", "disassociate", macAddr])

    if drop_return == 0:  # We dropped the connection successfully
        log("drop_connection", "Mac Address %s is being dropped." % macAddr, logLevels.DEBUG)
    else:
        log("drop_connection", "An error occured while dropping the Mac Address of: %s" % macAddr, logLevels.ERROR)

def error(tag, e):
    try:
        log(tag, "MySQL Error [%d]: %s" % (e.args[0], e.args[1]), logLevels.ERROR)
    except IndexError:
        log(tag, "MySQL Error: %s" % str(e), logLevels.ERROR)

def update_rad_check(dataBase, cursor):
    try:
        if sessionMode == sessionModes.DEVICE:
            cursor.execute("INSERT INTO radcheck (username, attribute, op, value) SELECT radcheck.username, 'Auth-Type', ':=', 'Reject' FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.attribute='Session-Timeout' AND TIMESTAMPDIFF(SECOND, radacct.acctstarttime, NOW()) > radcheck.value;")
            if int(cursor.rowcount) > 0:
                log("update_rad_check", "we have updated radcheck", logLevels.DEBUG)
        else:
            cursor.execute("INSERT INTO radcheck (username, attribute, op, value) SELECT radcheck.username, 'Auth-Type', ':=', 'Reject' FROM radcheck WHERE radcheck.attribute='Vendor-Specific' AND STR_TO_DATE(radcheck.value, '%Y-%m-%d %H:%i:%s') < STR_TO_DATE(UTC_TIMESTAMP(), '%Y-%m-%d %H:%i:%s');")

            regen = False
            if int(cursor.rowcount) > 0:
                log("update_rad_check", "Regenerating access code for AP mode...", logLevels.INFO)
                disassociate(cursor)
                regen = True
            else:  # check for empty db
                cursor.execute("SELECT * from radcheck where username LIKE 'qwifi%';")
                if cursor.rowcount == 0:
                    log("update_rad_check", "Generating access code for AP mode...", logLevels.INFO)
                    regen = True

            if regen:
                pwsize = 10
                username = 'qwifi' + ''.join(random.sample(string.ascii_lowercase, pwsize))
                password = ''.join(random.sample(string.ascii_lowercase, pwsize))
                query = "INSERT INTO radcheck SET username='%(username)s',attribute='Cleartext-Password',op=':=',value='%(password)s';" % { 'username' : username, 'password' : password }
                cursor.execute(query)
                query = "INSERT INTO radcheck (username,attribute,op,value) VALUES ('%(username)s', 'Vendor-Specific', ':=', DATE_FORMAT(UTC_TIMESTAMP() + INTERVAL %(timeout)s SECOND, '%%Y-%%m-%%d %%H:%%i:%%s'));" % { 'username' : username, 'timeout' : Config.get('session', 'timeout') }
                cursor.execute(query)

        dataBase.commit()
    except MySQLdb.Error, e:
        error("update_rad_check", e)
        dataBase.rollback()
        sys.exit()

def disassociate(cursor):
    cursor.execute("SELECT radacct.callingstationId FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.value = 'Reject' AND radacct.acctstoptime is NULL AND radacct.username LIKE 'qwifi%';")
    mac_addresses = set(cursor.fetchall())
    for macAddr in mac_addresses:
        log("dissassociate", "dropping %s" % macAddr, logLevels.DEBUG)
        threading.Thread(target=drop_connection(macAddr[0].replace('-', ':')))

def cull(dataBase, cursor):
    try:
        cursor.execute("SELECT username FROM radcheck WHERE value = 'Reject';")
        users_culled = cursor.fetchall()
        for user in users_culled:
            log("cull", "Removing user %s from radcheck." % user, logLevels.DEBUG)
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
        print "[" + tag + "]" + message
    if level != logLevels.NONE and level <= logLevel:
        if level == logLevels.ERROR:
            syslog.syslog(syslog.LOG_ERR, "[" + tag + "]" + message)
        elif level == logLevels.WARNING:
            syslog.syslog(syslog.LOG_WARNING, "[" + tag + "]" + message)
        elif level == logLevels.INFO:
            syslog.syslog(syslog.LOG_INFO, "[" + tag + "]" + message)
        elif level == logLevels.DEBUG:
            syslog.syslog(syslog.LOG_DEBUG, "[" + tag + "]" + message)
        else:
            syslog.syslog("[UNKNOWN MODE]" + message)

def main():
    global server
    global user
    global password
    global database

    log('main', 'Started logging process on daemon', logLevels.DEBUG)
    while True:
        new_config_time_stamp = os.path.getmtime(args.c)
        if config_time_stamp != new_config_time_stamp:
            parse_config_file(args.c)
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
            raise

        # print "We have opened MySQLdb successfully!"

        update_rad_check(db, cursor)  # update radcheck with reject for old sessions
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
            parse_config_file(args.c)
            main()
        else:
            try:
                test_premission = open("/var/run/qwifi45.pid", 'a')
                test_premission.close()
                os.remove("/var/run/qwifi45.pid")
            except IOError:
                log('main', 'qwifi.pid File not found or program running without admin permissions', logLevels.ERROR)
                print "Please run qwifi as admin."
                sys.exit()
            parse_config_file(args.c)
            with daemon.DaemonContext(working_directory='.', pidfile=daemon.pidlockfile.PIDLockFile("/var/run/qwifi.pid"), stderr=sys.stderr):
                main()
    else:
        print "Service is already running."
