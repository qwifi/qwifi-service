#!/usr/bin/python
#use the daemon script to launch this. 
#You can end the service by either using the daemon script or writing the word done to test.txt
count = 0

while True:
	f = open('test.txt', 'r+')
	count = count + 1
	if f.readline() == 'done':
		f.write('Count was: ' + str(count)) 
		break;
	f.close()