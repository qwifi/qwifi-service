from qrencode import Encoder
import string, random
import MySQLdb

def application(environ, start_response):
	db = MySQLdb.connect("localhost","rad","rad","radius")#host, user, password, db
	c = db.cursor()

	pwsize = 10
	user = ''.join(random.sample(string.ascii_lowercase, pwsize))
	password = ''.join(random.sample(string.ascii_lowercase, pwsize))

	sql = "INSERT INTO radcheck SET username=\'" + user + "\',attribute='Cleartext-Password',op=':=',value=\'" + password + "\';"

	try:
 		#Execute the sql command
 		c.execute(sql)
  		#commit the changes to the database
  		db.commit()
	except:
  		#Something bad happened rollback the changes
  		db.rollback()
  		print("Error: Inserting into DATABASE")

  	sql = "SELECT * FROM radcheck;"
	c.execute(sql)
	data = c.fetchall()
	current = data[-1]
	#code = current[1] +";" +current[4] +";;"

	code = "WIFI:T:WPAEAP;S:qwifi;P:" + current[4] + ";H:false;U:" + current[1] + ";E:PEAP;N:MSCHAPV2;;"

	enc = Encoder()
	im = enc.encode(code, {'width':200})
	im.save("/tmp/out.png")
	status = '200 OK'
	response_headers = [('Content-type', 'image/png')] 
	start_response(status, response_headers)
	return file("/tmp/out.png")
	#return [output]