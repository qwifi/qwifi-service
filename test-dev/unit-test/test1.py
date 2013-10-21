import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))
import qwifi
import MySQLdb
from subprocess import call

class Test1(unittest.TestCase):
	def setup(self):
		call(["sudo", "service", "mysql", "stop"])
	
	def tearDown(self):
		call(["sudo", "service", "mysql", "start"])

	def test_SetDbVar(self):
		qwifi.ConfigDbPath("")
		qwifi.SetDbVar()
		self.assertEqual(qwifi.server, 'localhost')
		self.assertEqual(qwifi.user,'root')
		self.assertEqual(qwifi.database, 'radius')
		self.assertEqual(qwifi.password, 'password')
		self.assertEqual(qwifi.logLevel, 4)

	def test_DbConnectException(self):#test for graceful exception handling if mysql is off
  		self.assertRaises(MySQLdb.Error, qwifi.main)


if __name__ == '__main__':
	unittest.main()