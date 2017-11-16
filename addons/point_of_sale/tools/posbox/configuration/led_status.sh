#!/usr/bin/env bash

set_brightness() {
    echo "${1}" > /sys/class/leds/led0/brightness
}

check_status_loop() {
    while true ; do
	if wget --quiet localhost:8069/hw_proxy/hello -O /dev/null ; then
	    set_brightness 255
	else
	    set_brightness 0
	fi
        sleep 5
    done
}

echo 'Get Odoo repository to follow odoo/8.0'
echo 'Mounting RW'
sudo mount / -o remount,rw
cd /home/odoo/pi/odoo
echo 'git remote add'
git remote add -t 8.0 odoo https://github.com/odoo/odoo.git
git config core.sparsecheckout true
echo 'git fetch'
git fetch odoo --depth=1
echo "addons/web
addons/web_kanban
addons/hw_*
addons/point_of_sale/tools/posbox/configuration
openerp/
odoo.py" | tee --append .git/info/sparse-checkout > /dev/null
echo 'checkouting 8.0 and read-tree it'
git checkout 8.0
git read-tree -mu HEAD
echo 'Reboot'
sudo reboot


echo none > /sys/class/leds/led0/trigger
check_status_loop
