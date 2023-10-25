#!/bin/bash

if [ -z "$SERVER_DIR" ]
then
    current_cwd=$(pwd)
    export SERVER_DIR="$current_cwd"
fi

WATCH_CMD="python3 $SERVER_DIR/logwatch_ooba.py"
WATCH_PID=$(ps aux | grep "$WATCH_CMD" | grep -v grep | awk '{print $2}')

while ! [ -z "$WATCH_PID" ]
do
    echo "Killing process $WATCH_PID running: $WATCH_CMD"
    kill "$WATCH_PID"
    sleep 2
    WATCH_PID=$(ps aux | grep "$WATCH_CMD" | grep -v grep | awk '{print $2}')
done

touch $SERVER_DIR/infer.log
tail -f -n +1 $SERVER_DIR/infer.log | $WATCH_CMD 2>&1 | tee $SERVER_DIR/watch.log &
echo "started logwatch"