import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))
import qwifi
import MySQLdb
from subprocess import call
######################### QWIFI UNIT TEST # 1 ###############################
#This unit test is design to test functionality(including exception handling)
#of our qwifi service while mysql is not an active service.
#Tests include: 
#1)Making sure SetDbVar gets the right values from config file
#2)A proper exception is raised when trying to connect to the database
#############################################################################
class Test1(unittest.TestCase):
	#Set up test enviroment
	def setup(self):
		call(["sudo", "service", "mysql", "stop"])
	
	#leave my pc in a good state
	def tearDown(self):
		call(["sudo", "service", "mysql", "start"])

	#test that SetDbVar gets the correct values from config file
	def test_SetDbVar(self):
		qwifi.ConfigDbPath("")
		qwifi.SetDbVar()
		self.assertEqual(qwifi.server, 'localhost')
		self.assertEqual(qwifi.user,'root')
		self.assertEqual(qwifi.database, 'radius')
		self.assertEqual(qwifi.password, 'password')
		self.assertEqual(qwifi.logLevel, 4)

	#test for graceful exception handling if mysql is off
	def test_DbConnectException(self):
  		self.assertRaises(MySQLdb.Error, qwifi.main)


if __name__ == '__main__':
	unittest.main()