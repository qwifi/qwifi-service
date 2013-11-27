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

log_levels = ("NONE", "ERROR", "WARNING", "INFO", "DEBUG")  # to add a new mode we just need another tuple entry
# create class logLevels with attributes that are members of logLevels tuple
log_levels = namedtuple("logLevels", log_levels)(*range(len(log_levels)))
log_level = log_levels.WARNING

session_modes = ("DEVICE", "AP")
session_modes = namedtuple("sessionModes", session_modes)(*range(len(session_modes)))
session_mode = ""

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
    global log_level
    global session_mode
    global config_time_stamp
    config_time_stamp = os.path.getmtime(path)
    Config.read(path)

    try:
        server = config_section_map("database")['server']
        user = config_section_map("database")['username']
        password = config_section_map("database")['password']
        database = config_section_map("database")['database']
        log_level = log_levels._asdict()[config_section_map("logging")['level'].upper()]
        session_mode = session_modes._asdict()[config_section_map("session")['mode'].upper()]
    except ConfigParser.NoSectionError:
        print "User Error", "File does NOT exist or file path NOT valid."
        raise

#uses hostapd_cli to kick a device off the network
def drop_connection(macAddr):
    drop_return = subprocess.call(["hostapd_cli", "disassociate", macAddr])

    if drop_return == 0:  # We dropped the connection successfully
        log("drop_connection", "MAC Address %s is being dropped." % macAddr, log_levels.DEBUG)
    else:
        log("drop_connection", "An error occured while dropping the MAC Address of: %s" % macAddr, log_levels.ERROR)


def db_error(tag, e):
    log(tag, "MySQL Error [%d]: %s" % (e.args[0], e.args[1]), log_levels.ERROR)


#updates radcheck to signal connections that should be dropped/culled.
def update_radcheck(dataBase, cursor):
    try:
        if session_mode == session_modes.DEVICE:
            cursor.execute(
                "INSERT INTO radcheck (username, attribute, op, value) SELECT radcheck.username, 'Auth-Type', ':=', 'Reject' FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.attribute='Session-Timeout' AND TIMESTAMPDIFF(SECOND, radacct.acctstarttime, NOW()) > radcheck.value;")
            if int(cursor.rowcount) > 0:
                log("update_rad_check", "we have updated radcheck", log_levels.DEBUG)
        else:
            cursor.execute(
                "INSERT INTO radcheck (username, attribute, op, value) SELECT radcheck.username, 'Auth-Type', ':=', 'Reject' FROM radcheck WHERE radcheck.attribute='Vendor-Specific' AND STR_TO_DATE(radcheck.value, '%Y-%m-%d %H:%i:%s') < STR_TO_DATE(UTC_TIMESTAMP(), '%Y-%m-%d %H:%i:%s');")

            regen = False
            if int(cursor.rowcount) > 0:
                log("update_rad_check", "Regenerating access code for AP mode...", log_levels.INFO)
                disassociate(cursor)
                regen = True
            else:  # check for empty db
                cursor.execute("SELECT * from radcheck where username LIKE 'qwifi%';")
                if cursor.rowcount == 0:
                    log("update_rad_check", "Generating access code for AP mode...", log_levels.INFO)
                    regen = True

            if regen:
                pwsize = 10
                username = 'qwifi' + ''.join(random.sample(string.ascii_lowercase, pwsize))
                password = ''.join(random.sample(string.ascii_lowercase, pwsize))
                query = "INSERT INTO radcheck SET username='%(username)s',attribute='Cleartext-Password',op=':=',value='%(password)s';" % {
                    'username': username, 'password': password}
                cursor.execute(query)
                query = "INSERT INTO radcheck (username,attribute,op,value) VALUES ('%(username)s', 'Vendor-Specific', ':=', DATE_FORMAT(UTC_TIMESTAMP() + INTERVAL %(timeout)s SECOND, '%%Y-%%m-%%d %%H:%%i:%%s'));" % {
                    'username': username, 'timeout': Config.get('session', 'timeout')}
                cursor.execute(query)

        dataBase.commit()
    except MySQLdb.Error, e:
        db_error("update_rad_check", e)
        dataBase.rollback()
        sys.exit()

# Generate a list of freeloader connections (skips the first connection associated with user x,
# which is assumed to be valid)
def freeloader_gen(duplicates):
    previous = ()
    for entry in duplicates:
        if entry[0] == previous:
            yield entry[1]
        previous = entry[0]

#compiles a list of machines that should be kicked off the network then issues the command to kick them off all at once.
def disassociate(cursor):
    cursor.execute(
        "SELECT radacct.callingstationId FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.value = 'Reject' AND radacct.acctstoptime is NULL AND radacct.username LIKE 'qwifi%';")
    mac_addresses = [result[0] for result in cursor.fetchall()]
    cursor.execute(
        "select username,callingstationid, UNIX_TIMESTAMP(acctstarttime) as DATE from radacct WHERE acctstoptime is NULL GROUP BY username,callingstationid ORDER BY DATE ASC;")
    if session_mode == session_modes.DEVICE:
        mac_addresses = set(mac_addresses + [fl for fl in freeloader_gen(cursor.fetchall())])
    for mac_address in mac_addresses:
        log("disassociate", "dropping %s" % mac_address, log_levels.DEBUG)
        threading.Thread(target=drop_connection(mac_address.replace('-', ':')))

#removes outdated information from the database
def cull(dataBase, cursor):
    try:
        cursor.execute("SELECT username FROM radcheck WHERE value = 'Reject';")
        users_culled = cursor.fetchall()
        for user in users_culled:
            log("cull", "Removing user %s from radcheck." % user, log_levels.DEBUG)
        cursor.execute(
            "DELETE FROM radcheck WHERE username IN (SELECT username FROM (SELECT username FROM radcheck WHERE value='Reject') temp);")
        if int(cursor.rowcount) > 0:
            log("cull", "We have deleted %s things from radcheck" % cursor.rowcount, log_levels.DEBUG)
        dataBase.commit()
    except MySQLdb.Error, e:
        db_error("cull", e)
        dataBase.rollback()

# A general log function, the modes are normal, Error, Warning, Debug
def log(tag, message, level):
    if mode == modes.FOREGROUND:
        print "[" + tag + "]" + message
    if level != log_levels.NONE and level <= log_level:
        if level == log_levels.ERROR:
            syslog.syslog(syslog.LOG_ERR, "[" + tag + "]" + message)
        elif level == log_levels.WARNING:
            syslog.syslog(syslog.LOG_WARNING, "[" + tag + "]" + message)
        elif level == log_levels.INFO:
            syslog.syslog(syslog.LOG_INFO, "[" + tag + "]" + message)
        elif level == log_levels.DEBUG:
            syslog.syslog(syslog.LOG_DEBUG, "[" + tag + "]" + message)
        else:
            syslog.syslog("[UNKNOWN MODE]" + message)
    else:
            syslog.syslog("[INVALID] Tried to log with invalid level.")

#the main controller of the service. Loops forever untill the service is killed. This is where everything happens!
def main():
    global server
    global user
    global password
    global database

    log('main', 'Started logging process on daemon', log_levels.DEBUG)
    while True:
        try:
            db = MySQLdb.connect(server, user, password, database)
        except MySQLdb.Error, e:
            db_error("main", e)
            raise
        try:
            cursor = db.cursor()
        except MySQLdb.Error, e:
            print "blah."
            log("main", e, log_levels.ERROR)
            raise

        # print "We have opened MySQLdb successfully!"
        new_config_time_stamp = os.path.getmtime(args.c)
        if config_time_stamp != new_config_time_stamp:
            parse_config_file(args.c)
            if session_mode == session_modes.AP:
                try:
                    cursor.execute("DELETE FROM radcheck WHERE username LIKE 'qwifi%';")
                    db.commit()
                except MySQLdb.Error, e:
                    db_error("main", e)
                    db.rollback()
                    raise

        update_radcheck(db, cursor)  # update radcheck with reject for old sessions
        disassociate(cursor)  # kick off all of the old sessions
        cull(db, cursor)  # remove unneccassery data from DB
        time.sleep(5)  # loop every 5 seconds

# parsing through the command line arguments.
def parse_args():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", action="store_true", help="Displays messages to the foreground(stdout) or syslog.")
    parser.add_argument("-c", default="qwifi.conf", help="allows you to designate where qwifi.conf is located.")
    return parser.parse_args()

#set up the state of the service and launch the main controller function.
if __name__ == '__main__':
    args = parse_args()
    if not os.path.exists("/var/run/qwifi.pid.lock"):
        if args.n == True:
            mode = modes.FOREGROUND
            log_level = log_levels.DEBUG
            parse_config_file(args.c)
            main()
        else:
            if os.geteuid() != 0:
                log('main', 'qwifi.pid File not found or program running without admin permissions', log_levels.ERROR)
                print "Please run qwifi as admin."
                sys.exit()
            parse_config_file(args.c)
            with daemon.DaemonContext(working_directory='.',
                                      pidfile=daemon.pidlockfile.PIDLockFile("/var/run/qwifi.pid"), stderr=sys.stderr):
                main()
    else:
        print "Service is already running."
