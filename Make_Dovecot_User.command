#!/bin/zsh

sudo dscl . -create /Groups/_dovecot
sudo dscl . -create /Groups/_dovecot UniqueID 30
sudo dscl . -create /Users/_dovecot
sudo dscl . -create /Users/_dovecot UserShell /bin/false
sudo dscl . -create /Users/_dovecot RealName "Dovecot IMAP Server"
sudo dscl . -create /Users/_dovecot UniqueID 30
sudo dscl . -create /Users/_dovecot PrimaryGroupID 30
sudo dscl . -create /Users/_dovecot NFSHomeDirectory /opt/local/var/run/dovecot

sudo defaults write /Library/Preferences/com.apple.loginwindow HiddenUsersList -array-add _fetchmail _dovecot

sudo dscl . -create /Users/_dovenull
sudo dscl . -create /Users/_dovenull UserShell /bin/false
sudo dscl . -create /Users/_dovenull RealName "Dovecot IMAP Server"
sudo dscl . -create /Users/_dovenull UniqueID 31
sudo dscl . -create /Users/_dovenull PrimaryGroupID 30
sudo dscl . -create /Users/_dovenull NFSHomeDirectory /opt/local/var/run/dovecot

sudo defaults write /Library/Preferences/com.apple.loginwindow HiddenUsersList -array-add _fetchmail _dovenull

#vim: set nowrap tabstop=8 shiftwidth=4 softtabstop=4 expandtab :
#vim: set textwidth=0 filetype=zsh foldmethod=marker nospell :
