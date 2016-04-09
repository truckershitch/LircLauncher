#!/bin/bash
#openbox &
irxevent &
irexec &
/usr/bin/google-chrome-unstable --kiosk "$@"
kill %1
kill %2
kill %3
