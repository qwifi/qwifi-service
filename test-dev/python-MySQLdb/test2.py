from qrencode import Encoder
import string, random
import MySQLdb

db = MySQLdb.connect("localhost","rad","rad","radius")#host, user, password, db
c = db.cursor()

pwsize = 10
user = ''.join(random.sample(string.ascii_lowercase, pwsize))
password = ''.join(random.sample(string.ascii_lowercase, pwsize))

sql = "INSERT INTO radcheck SET username=\'" + user + "\',attribute='Cleartext-Password',op=':=',password=\'" + password + "\';"
#sql = "INSERT INTO radcheck(USERNAME, ATTRIBUTE, OP, VALUE) VALUES(\'" + user +"\',\'Cleartext-Password',\':=\',\'" + password + "\';"
print sql
try:
  #Execute the sql command
  c.execute(sql)
  #commit the changes to the database
  db.commit()
except:
  #Something bad happened rollback the changes
  db.rollback()
  print("Error: Inserting into DATABASE")

#enc = Encoder()
#im = enc.encode('http://www.gamefaqs.com', {'width':100})
#im.save("out.png")
#status = '200 OK'
#response_headers = [('Content-type', 'image/png')] 
#start_response(status, response_headers)
#return file("/tmp/out.png")