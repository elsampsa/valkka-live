#!/bin/bash
echo
echo For this to work you need to install gdb
echo and run a version of libValkka that has the debug symbols enabled
echo
echo type 'run' to start running, 'bt' to show the backtrace, 'exit' to exit
echo
gdb --args python3 valkka/live/main.py $@
