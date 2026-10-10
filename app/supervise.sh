#!/bin/sh
# No cron/systemd on this box: this loop is the watchdog (checks every 5 min). Started from ~/.profile at login/boot.
cd "$(dirname "$0")"
[ -f supervise.pid ] && kill -0 "$(cat supervise.pid)" 2>/dev/null && exit 0
echo $$ > supervise.pid
while true; do ./watchdog.sh; sleep 300; done
