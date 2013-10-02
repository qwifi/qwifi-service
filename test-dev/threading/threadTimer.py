#!/usr/bin/python
import threading
from threading import Timer
import daemon
import time
import os
import logging
import logging.handlers
import datetime

l = threading.Lock()
def delete(sleepFor):
	time.sleep(sleepFor)
	l.acquire()
	logging.info(str(datetime.datetime.now())+ " -------Deleted File")
	l.release()
	os.remove("done.txt")


def main():
	logging.basicConfig(filename='log.out', level=logging.DEBUG)
	while True:
		f = open("done.txt", 'r')
		x = f.readline()
		if x == "quit" or x =="quit\n":
			l.acquire()
			logging.info(str(datetime.datetime.now())+ " ------Quit Successful")
			l.release()
			f.close()
			break;
		else:
			try:
				t = threading.Thread(target=delete(float(x)))
				t.start()
			except ValueError:
				l.acquire()
				logging.warning(str(datetime.datetime.now()) + " -------Value Error")
				l.release()
		f.close()
		time.sleep(5.0)
		
with daemon.DaemonContext(working_directory = '.'):
	main()