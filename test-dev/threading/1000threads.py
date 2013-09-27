import threading
from threading import Timer
import time

def hello():
	time.sleep(60)
	print "Hello!!"



for i in range(0,1000):
	print "starting timer " + str(i)
	threading.Thread(target=hello).start()