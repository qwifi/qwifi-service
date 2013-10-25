import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
import qwifi
import MySQLdb
from subprocess import call
class DataBaseTest(unittest.TestCase):
    #test that SetDbVar gets the correct values from config file
    def test_DataBaseVar(self):
        qwifi.parseConfigFile("qwifi.conf")
        self.assertEqual(qwifi.server, 'localhost')
        self.assertEqual(qwifi.user,'root')
        self.assertEqual(qwifi.database, 'radius')
        self.assertEqual(qwifi.password, 'password')
        self.assertEqual(qwifi.logLevel, 4)

    #test for graceful exception handling if mysql is off
    def test_DbConnectException(self):
       call(["sudo", "service", "mysql", "stop"])
       self.assertRaises(MySQLdb.Error, qwifi.main)
       call(["sudo", "service", "mysql", "start"])

    def test_RadiusExists(self):
        qwifi.parseConfigFile("qwifi.conf")
        db = MySQLdb.connect(qwifi.server,qwifi.user,qwifi.password,qwifi.database)
        cursor = db.cursor()
        cursor.execute("SHOW DATABASES LIKE 'radius'")
        rad = cursor.fetchall()
        self.assertEqual(len(rad),1)

    def test_TablesExist(self):
        qwifi.parseConfigFile("qwifi.conf")
        db = MySQLdb.connect(qwifi.server,qwifi.user,qwifi.password,qwifi.database)
        cursor = db.cursor()
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
        qwifi.parseConfigFile("qwifi.conf")
        os.system("mysqldump -u " + qwifi.user +" -p" + qwifi.password + " " + qwifi.database + " > " + "backup.sql" )
        os.system("mysql -u " + qwifi.user +" -p" + qwifi.password + " -h " + qwifi.server + " " + qwifi.database + " < " + "test.sql" )
        db = MySQLdb.connect(qwifi.server,qwifi.user,qwifi.password,qwifi.database)
        cursor = db.cursor()
        qwifi.updateRadcheck(db, cursor)
        cursor.execute("SELECT * from radcheck;")
        self.assertEqual(len(cursor.fetchall()), 6)
        os.system("mysql -u " + qwifi.user +" -p" + qwifi.password + " -h " + qwifi.server + " " + qwifi.database + " < " + "backup.sql" )


if __name__ == '__main__':
    unittest.main()