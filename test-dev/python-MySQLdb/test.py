#!/usr/bin/python
import string, random
import MySQLdb

#open database connection
db = MySQLdb.connect("localhost", "test", "test123", "TEST")

cursor = db.cursor()

cursor.execute("DROP TABLE IF EXISTS AUTHENTICATION")
sql = """CREATE TABLE AUTHENTICATION (
         USER CHAR(30) NOT NULL,
         PASSWORD CHAR(50) NOT NULL)"""

cursor.execute(sql)




pwsize = 20
for x in range(0,50):
	user = "user" + '%03d' % x;
	password = ''.join(random.sample(string.ascii_lowercase, pwsize))#generate random string password
	sql = "INSERT INTO AUTHENTICATION(USER, PASSWORD) VALUES(\'" + user + "\', \'" + password + "\')"
	try:
	  #Execute the sql command
	  cursor.execute(sql)
	  #commit the changes to the database
	  db.commit()
	except:
	  #Something bad happened rollback the changes
	  db.rollback()
	  print("Error: Inserting into TEST DATABASE")
