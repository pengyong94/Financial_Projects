#!/bin/bash

# ./start_server.sh start
# ./start_server.sh stop
# ./start_server.sh restart
# ./start_server.sh status

# 定义变量
SERVICE_NAME="Change_Task_Agent"
SCRIPT_PATH="src/main.py"
PIDFILE="logs/${SERVICE_NAME}.pid"
LOGFILE="logs/${SERVICE_NAME}.log"

start() {
    echo "Starting $SERVICE_NAME..."
    if [ -f $PIDFILE ]; then
        if kill -0 $(cat $PIDFILE) > /dev/null 2>&1; then
            echo "$SERVICE_NAME is already running."
            return 1
        else
            rm -f $PIDFILE
        fi
    fi

    nohup python3 $SCRIPT_PATH >> $LOGFILE 2>&1 &
    echo $! > $PIDFILE
    echo "$SERVICE_NAME started."
}

stop() {
    echo "Stopping $SERVICE_NAME..."
    if [ ! -f $PIDFILE ] || ! kill -0 $(cat $PIDFILE) > /dev/null 2>&1; then
        echo "$SERVICE_NAME is not running."
        rm -f $PIDFILE
        return 1
    fi
    kill $(cat $PIDFILE)
    wait $(cat $PIDFILE) 2>/dev/null
    rm -f $PIDFILE
    echo "$SERVICE_NAME stopped."
}

restart() {
    stop
    start
}

status() {
    if [ -f $PIDFILE ] && kill -0 $(cat $PIDFILE) > /dev/null 2>&1; then
        echo "$SERVICE_NAME is running."
    else
        echo "$SERVICE_NAME is not running."
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
esac

exit 0