#!/bin/sh

#sudo cp -p Firewall.hermes /Library/StartupItems/Firewall/Firewall
sudo cp -p Firewall.hermes.sgu /Library/StartupItems/Firewall/Firewall
sudo chown root:wheel /Library/StartupItems/Firewall/Firewall
sudo chmod 755 /Library/StartupItems/Firewall/Firewall

sudo /Library/StartupItems/Firewall/Firewall start
