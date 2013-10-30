#!/usr/bin/python
##########################################################
#   This unit test requires an unversioned qwifi.conf to #
#   live in the same directory as DataBaseTest.py        #
##########################################################
import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
import qwifi
import MySQLdb
from subprocess import call
class DataBaseTest(unittest.TestCase):
    #test that parseConfigFile gets the correct values from config file
    def test_ParseConfigFile(self):
        #load config file
        qwifi.parse_config_file("test.conf")
        #make sure the expected values were loaded
        self.assertEqual(qwifi.server, 'localhost')
        self.assertEqual(qwifi.user,'root')
        self.assertEqual(qwifi.database, 'radius')
        self.assertEqual(qwifi.password, 'password')
        self.assertEqual(qwifi.logLevel, 4)
    
    def test_DissasociateQuery(self):
        qwifi.parse_config_file("qwifi.conf")
        #backup current radius database
        os.system("mysqldump -u " + qwifi.user +" -p" + qwifi.password + " " + qwifi.database + " > " + "backup.sql" )
        #load the test database
        os.system("mysql -u " + qwifi.user +" -p" + qwifi.password + " -h " + qwifi.server + " " + qwifi.database + " < " + "test.sql" )
        db = MySQLdb.connect(qwifi.server,qwifi.user,qwifi.password,qwifi.database)
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
        os.system("mysql -u " + qwifi.user +" -p" + qwifi.password + " -h " + qwifi.server + " " + qwifi.database + " < " + "backup.sql" )

    def test_Cull(self):
        qwifi.parse_config_file("qwifi.conf")
        os.system("mysqldump -u " + qwifi.user +" -p" + qwifi.password + " " + qwifi.database + " > " + "backup.sql" )
        os.system("mysql -u " + qwifi.user +" -p" + qwifi.password + " -h " + qwifi.server + " " + qwifi.database + " < " + "test.sql" )
        db = MySQLdb.connect(qwifi.server,qwifi.user,qwifi.password,qwifi.database)
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
        #find the rest of the entries in radcheck (there should be one)
        cursor.execute("SELECT * FROM radcheck;")
        self.assertEqual(len(cursor.fetchall()), 1)
        db.close()
        os.system("mysql -u " + qwifi.user +" -p" + qwifi.password + " -h " + qwifi.server + " " + qwifi.database + " < " + "backup.sql" )


    #test for graceful exception handling if mysql is off
    def test_DbConnectException(self):
       call(["sudo", "service", "mysql", "stop"])
       self.assertRaises(MySQLdb.Error, qwifi.main)
       call(["sudo", "service", "mysql", "start"])

    def test_RadiusExists(self):
        qwifi.parse_config_file("qwifi.conf")
        db = MySQLdb.connect(qwifi.server,qwifi.user,qwifi.password,qwifi.database)
        cursor = db.cursor()
        cursor.execute("SHOW DATABASES LIKE 'radius'")
        rad = cursor.fetchall()
        #if len of rad = 1 there is exactly one database named radius
        self.assertEqual(len(rad),1)

    def test_TablesExist(self):
        qwifi.parse_config_file("qwifi.conf")
        db = MySQLdb.connect(qwifi.server,qwifi.user,qwifi.password,qwifi.database)
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

    def test_UpdateRadcheck(self):
        qwifi.parse_config_file("qwifi.conf")
        os.system("mysqldump -u " + qwifi.user +" -p" + qwifi.password + " " + qwifi.database + " > " + "backup.sql" )
        os.system("mysql -u " + qwifi.user +" -p" + qwifi.password + " -h " + qwifi.server + " " + qwifi.database + " < " + "test.sql" )
        db = MySQLdb.connect(qwifi.server,qwifi.user,qwifi.password,qwifi.database)
        cursor = db.cursor()
        #let updateRadcheck do it's job
        qwifi.update_rad_check(db, cursor)
        #three new entries should be added to radcheck 3 (original) + 3 (new) == 6 entries
        cursor.execute("SELECT * from radcheck;")
        self.assertEqual(len(cursor.fetchall()), 6)
        db.close()
        os.system("mysql -u " + qwifi.user +" -p" + qwifi.password + " -h " + qwifi.server + " " + qwifi.database + " < " + "backup.sql" )


if __name__ == '__main__':
    unittest.main()