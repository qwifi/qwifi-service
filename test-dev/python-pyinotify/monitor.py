import os
from pyinotify import WatchManager, Notifier, ThreadedNotifier, EventsCodes, ProcessEvent
import pyinotify
import string, random

auth = 8 # number of chars for username/password
wm = WatchManager()

mask = pyinotify.IN_DELETE | pyinotify.IN_CLOSE_WRITE  # watched events

class PTmp(ProcessEvent):
    def process_IN_CLOSE_WRITE(self, event):
        path = os.path.join(event.path, event.name)
        print "WRITE: %s" %  path
        if os.path.splitext(path)[1] == '.txt' and os.stat(path)[6] == 0: #if extension is .txt and the file is empty
            username = ''.join(random.sample(string.ascii_lowercase, auth))#generate random string username
            password = ''.join(random.sample(string.ascii_lowercase, auth))#generate random string password
            f = open(str(path), 'a')
            f.write(username + '/') #print username to file plus /
            f.write(password) #print password to file.. Format: username/password
            f.close()

        #def process_IN_DELETE(self, event):       # couldn't get this event to trigger
         #   print "Remove: %s" %  os.path.join(event.path, event.name)
            #if event.name == 'done.txt':
         #   notifier.stop()



notifier = Notifier(wm, PTmp())

wdd = wm.add_watch('monitor_me', mask, rec=True)

while True:  # loop forever
    try:
        # process the queue of events as explained above
        notifier.process_events()
        if notifier.check_events():
            # read notified events and enqeue them
            notifier.read_events()
        # you can do some tasks here...
    except KeyboardInterrupt:
        # destroy the inotify's instance on this interrupt (stop monitoring)
        notifier.stop()
        break