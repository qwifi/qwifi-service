#!/usr/bin/python
import threading
from threading import Timer
import daemon
import time
import os
import logging
import logging.handlers
import datetime

def delete(sleepFor):
	time.sleep(sleepFor)
	logging.info(str(datetime.datetime.now())+ " -------Deleted File")
	os.remove("done.txt")


def main():
	logging.basicConfig(filename='log.out', level=logging.DEBUG)
	while True:
		f = open("done.txt", 'r')
		x = f.readline()
		if x == "quit" or x =="quit\n":
			logging.info(str(datetime.datetime.now())+ " ------Quit Successful")
			f.close()
			break;
		else:
			try:
				threading.Thread(target=delete(float(x)))
			except ValueError:
				logging.warning(str(datetime.datetime.now()) + " -------Value Error")
		f.close()
		time.sleep(5.0)
		
with daemon.DaemonContext(working_directory = '.'):
	main()