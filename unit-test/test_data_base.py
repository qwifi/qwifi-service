#!/usr/bin/python
#   This unit test requires an unversioned qwifi.conf to #
#   live in the same directory as DataBaseTest.py        #

import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
sys.path.append('/usr/local/wsgi/resources/python/')
sys.path.append(os.path.join(os.path.dirname(__file__), '../../ui/resources/python/usr/local/wsgi/resources/python/'))
import qwifi
import MySQLdb
from subprocess import call
class DataBaseTest(unittest.TestCase):
    def setUp(self):
        global server
        global user
        global password
        global database
        global stdout_log

        qwifi.parse_config_file("qwifi.conf")
        server = qwifi.config.get('database', 'server')
        user = qwifi.config.get('database', 'username')
        password = qwifi.config.get('database', 'password')
        database = qwifi.config.get('database', 'database')

        stdout_log = open('test.out', 'a')
        call(["sudo", "service", "mysql", "start"], stdout=stdout_log)
        os.system("mysqldump -u " + user + " -p" + password + " " + database + " > " + "backup.sql")

    def tearDown(self):
        global stdout_log
        os.system("mysql -u " + user + " -p" + password + " -h " + server + " " + database + " < " + "backup.sql")
        stdout_log.close()

    #test that parseConfigFile gets the correct values from config file
    def test_parse_config_file(self):
        #load config file
        qwifi.parse_config_file("test.conf")
        #make sure the expected values were loaded
        self.assertEqual(qwifi.config.get('database', 'server'), 'localhost')
        self.assertEqual(qwifi.config.get('database', 'username'),'root')
        self.assertEqual(qwifi.config.get('database', 'database'), 'radius')
        self.assertEqual(qwifi.config.get('database', 'password'), 'password')
        self.assertEqual(qwifi.log_level, 4)
        self.assertEqual(qwifi.session_mode, 0)
    
    def test_disassociate_query(self):
        db = MySQLdb.connect(server, user, password, database)
        #load the test database
        os.system("mysql -u " + user +" -p" + password + " -h " + server + " " + database + " < " + "test.sql" )
        db = MySQLdb.connect(server, user, password, database)
        cursor = db.cursor()
        #dissasociate's main query
        cursor.execute("INSERT INTO radcheck (username, attribute, op, value) SELECT radcheck.username, 'Auth-Type', ':=', 'Reject' FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.attribute='Session-Timeout' AND TIMESTAMPDIFF(SECOND, radacct.acctstarttime, NOW()) > radcheck.value AND radacct.acctstoptime is NULL;")
        #look for the mac addresses that match radcheck entries with value=reject and stop time = NULL
        cursor.execute("SELECT radacct.callingstationId FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.value = 'Reject' AND radacct.acctstoptime is NULL;")
        results = cursor.fetchall()
        #exactly 3 mac addresses should be returned
        self.assertEqual(len(results), 3)
        #the mac address values should be 1,2, and 3.
        self.assertEqual(int(results[0][0]), 1)
        self.assertEqual(int(results[1][0]), 2)
        self.assertEqual(int(results[2][0]), 3)
        db.close()

    def test_cull(self):
        db = MySQLdb.connect(server, user, password, database)
        os.system("mysql -u " + user +" -p" + password + " -h " + server + " " + database + " < " + "test.sql" )
        db = MySQLdb.connect(server, user, password, database)
        cursor = db.cursor()
        #insert a new value to make sure cull only deletes what we want
        cursor.execute('INSERT INTO radcheck (username) VALUES("testtest");')
        #update radcheck
        cursor.execute("INSERT INTO radcheck (username, attribute, op, value) SELECT radcheck.username, 'Auth-Type', ':=', 'Reject' FROM radcheck INNER JOIN radacct ON radcheck.username=radacct.username WHERE radcheck.attribute='Session-Timeout' AND TIMESTAMPDIFF(SECOND, radacct.acctstarttime, NOW()) > radcheck.value AND radacct.acctstoptime is NULL;")
        #let cull do it's job        
        qwifi.cull(db, cursor)
        #find all radcheck entries where value = reject (there should be zero)
        cursor.execute("SELECT * FROM radcheck WHERE value='Reject';")
        self.assertEqual(len(cursor.fetchall()), 0)
        #find the rest of the entries in radcheck (there should be four)
        cursor.execute("SELECT * FROM radcheck;")
        self.assertEqual(len(cursor.fetchall()), 4)
        db.close()


    #test for graceful exception handling if mysql is off
    def test_db_connect_exception(self):
        db = MySQLdb.connect(server, user, password, database)
        cursor = db.cursor()
        call(["sudo", "service", "mysql", "stop"], stdout=stdout_log)
        with self.assertRaises(MySQLdb.Error):
            qwifi.main()
        with self.assertRaises(MySQLdb.OperationalError):
            qwifi.update_radcheck(db, cursor)
        with self.assertRaises(MySQLdb.Error):
            qwifi.cull(db, cursor)
        call(["sudo", "service", "mysql", "start"], stdout=stdout_log)

    def test_radius_exists(self):
        db = MySQLdb.connect(server, user, password, database)
        cursor = db.cursor()
        cursor.execute("SHOW DATABASES LIKE 'radius'")
        rad = cursor.fetchall()
        #if len of rad = 1 there is exactly one database named radius
        self.assertEqual(len(rad),1)

    def test_tables_exist(self):
        db = MySQLdb.connect(server, user, password, database)
        cursor = db.cursor()
        #these queries should all return a tuple of length 1
        cursor.execute("SHOW TABLES LIKE 'radacct'")
        self.assertEqual(len(cursor.fetchall()),1)
        cursor.execute("SHOW TABLES LIKE 'radcheck'")
        self.assertEqual(len(cursor.fetchall()),1)
        cursor.execute("SHOW TABLES LIKE 'radgroupcheck'")
        self.assertEqual(len(cursor.fetchall()),1)
        cursor.execute("SHOW TABLES LIKE 'radgroupreply'")
        self.assertEqual(len(cursor.fetchall()),1)
        cursor.execute("SHOW TABLES LIKE 'radpostauth'")
        self.assertEqual(len(cursor.fetchall()),1)
        cursor.execute("SHOW TABLES LIKE 'radreply'")
        self.assertEqual(len(cursor.fetchall()),1)
        cursor.execute("SHOW TABLES LIKE 'radusergroup'")
        self.assertEqual(len(cursor.fetchall()),1)

    def test_update_radcheck_device(self):
        qwifi.session_mode = qwifi.session_modes.DEVICE
        os.system("mysql -u " + user +" -p" + password + " -h " + server + " " + database + " < " + "test.sql" )
        db = MySQLdb.connect(server, user, password, database)
        cursor = db.cursor()
        #let updateRadcheck do it's job
        qwifi.update_radcheck(db, cursor)
        #three new entries should be added to radcheck 6 (original) + 3 (reject) == 6 entries
        cursor.execute("SELECT * from radcheck;")
        self.assertEqual(len(cursor.fetchall()), 9)
        db.close()

    def test_update_radcheck_ap(self):
        qwifi.session_mode = qwifi.session_modes.AP
        qwifi.config.set("session", "timeout", '10')
        os.system("mysql -u " + user +" -p" + password + " -h " + server + " " + database + " < " + "test.sql" )
        db = MySQLdb.connect(server, user, password, database)
        cursor = db.cursor()
        #let updateRadcheck do it's job
        qwifi.update_radcheck(db, cursor)
        #five new entries should be added to radcheck 6 (original) + 3 (reject) + 2 (regen) == 11 entries
        cursor.execute("SELECT * from radcheck;")
        self.assertEqual(len(cursor.fetchall()), 11)
        cursor.execute("DELETE from radcheck;")
        qwifi.update_radcheck(db, cursor)
        cursor.execute("SELECT * FROM radcheck;")
        self.assertEqual(len(cursor.fetchall()), 2)
        db.close()



if __name__ == '__main__':
    unittest.main()
