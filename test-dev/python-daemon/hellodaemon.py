#!/usr/bin/python
#Just run this program and it will update count until the test.txt file in pwd contains 'done'
import daemon
def main():
	print daemon.__file__
	count = 0
	while True:
		f = open('test.txt', 'r+')
		count = count + 1
		if f.readline() == 'done':
			f.write('Count was: ' + str(count)) 
			f.close()
			break
		f.close()

with daemon.DaemonContext(working_directory = '.'):
	main()
