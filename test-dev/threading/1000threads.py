import threading
from threading import Timer
import time

l = threading.Lock()

def hello():
	time.sleep(10)
	l.acquire()
	print "Hello!!"
	l.release()


for i in range(0,1000):
	print "starting timer " + str(i)
	self = threading.Thread(target=hello)
	#self.setDaemon(True)
	self.start()