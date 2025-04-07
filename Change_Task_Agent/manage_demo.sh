#!/bin/bash

# 服务管理脚本名称: manage_demo.sh
# 使用方法: ./manage_demo.sh [start|stop|restart|status]

APP_NAME="streamlit_demo"      # 应用名称
APP_DIR="."    # 应用目录路径（请修改为实际路径）
APP_FILE="demo.py"            # 入口文件名称
PORT=8009                     # 服务端口
PID_FILE="$APP_DIR/$APP_NAME.pid"  # PID文件路径
LOG_FILE="$APP_DIR/$APP_NAME.log"  # 日志文件路径

# 进入应用目录
cd $APP_DIR || exit 1

case "$1" in
    start)
        if [ -f $PID_FILE ]; then
            PID=$(cat $PID_FILE)
            if ps -p $PID > /dev/null 2>&1; then
                echo "Service $APP_NAME is already running (PID: $PID)"
                exit 0
            else
                echo "Removing orphan PID file"
                rm -f $PID_FILE
            fi
        fi

        echo "Starting $APP_NAME..."
        nohup streamlit run $APP_FILE --server.port $PORT > $LOG_FILE 2>&1 &
        NEW_PID=$!
        echo $NEW_PID > $PID_FILE
        echo "Service $APP_NAME started (PID: $NEW_PID)"
        ;;
    
    stop)
        if [ -f $PID_FILE ]; then
            PID=$(cat $PID_FILE)
            if ps -p $PID > /dev/null 2>&1; then
                echo "Stopping $APP_NAME (PID: $PID)..."
                kill $PID
                rm -f $PID_FILE
                echo "Service $APP_NAME stopped"
            else
                echo "Service $APP_NAME not running (orphan PID file)"
                rm -f $PID_FILE
            fi
        else
            echo "PID file not found - is the service running?"
        fi
        ;;
    
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    
    status)
        if [ -f $PID_FILE ]; then
            PID=$(cat $PID_FILE)
            if ps -p $PID > /dev/null 2>&1; then
                echo "Service $APP_NAME is running (PID: $PID)"
                echo "Port: $(lsof -Pan -p $PID -i | grep 'LISTEN' | awk '{print $9}')"
                exit 0
            else
                echo "Service $APP_NAME is dead (orphan PID file)"
                rm -f $PID_FILE
                exit 1
            fi
        else
            echo "Service $APP_NAME is not running"
            exit 3
        fi
        ;;
    
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac