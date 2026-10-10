#!/bin/sh
# Restart the hub if port 8080 does not answer. Run from cron every 5 min, and at boot.
cd "$(dirname "$0")"
curl -fs -m 20 -o /dev/null http://127.0.0.1:8080/sources.json && exit 0
pkill -f "python3 server.py" 2>/dev/null; sleep 1
nohup python3 server.py >> server.log 2>&1 &
echo "$(date '+%F %T') watchdog restarted server" >> watchdog.log
