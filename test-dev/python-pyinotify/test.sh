#!/bin/bash
if [ $1 = 'test' ]
then
	cd monitor_me
	touch test.txt
	cat test.txt
	echo ""
	rm test.txt
elif [ $1 = 'done' ]
then
	cd monitor_me
	rm -rf *
	echo "DELETE me to end process" > done.txt
fi
