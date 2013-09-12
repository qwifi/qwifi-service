#!/bin/bash
#type ./daemon_test.sh <program's file name> <start or stop>
#this will launch the program as a daemon.
#depends on the package python-zdaemon (http://packages.debian.org/unstable/zope/python-zdaemon)
if [ $2 = 'start' ]; 
	then
		zdaemon -p "python $1" -z . -d start
	else
		zdaemon -p "python $1" -z . -d stop
fi
