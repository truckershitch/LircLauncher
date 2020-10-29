#!/bin/bash
# Disable xscreensaver - kill it
#DISPLAY=:0 /usr/bin/xscreensaver-command -exit
# Run launcher then restart xscreensaver on exit
cd /home/truckershitch/LircLauncher
DISPLAY=:0 ./run.py > log.txt 2>&1
#/usr/bin/xscreensaver -no-splash

