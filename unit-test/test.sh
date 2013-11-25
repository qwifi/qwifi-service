#!/bin/bash
if [ $1 = 'all']
then
    python -m unittest discover
elif [$1 = 'log']
then
    ./testLog.py
elif [$1 = 'db']
then
    ./testDataBase.py
elif [$1 = 'util']
then
    ./testUtil.py
else
    echo "
