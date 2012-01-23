#!/bin/bash

dscl . -create /Groups/_dovecot
dscl . -create /Groups/_dovecot UniqueID 30

dscl . -create /Users/_dovecot
dscl . -create /Users/_dovecot UserShell /bin/false
dscl . -create /Users/_dovecot RealName "Dovecot IMAP Server"
dscl . -create /Users/_dovecot UniqueID 30
dscl . -create /Users/_dovecot PrimaryGroupID 30
dscl . -create /Users/_dovecot NFSHomeDirectory /opt/local/var/run/dovecot

dscl . -create /Users/_dovenull
dscl . -create /Users/_dovenull UserShell /bin/false
dscl . -create /Users/_dovenull RealName "Dovecot IMAP Server"
dscl . -create /Users/_dovenull UniqueID 31
dscl . -create /Users/_dovenull PrimaryGroupID 30
dscl . -create /Users/_dovenull NFSHomeDirectory /opt/local/var/run/dovecot

defaults write /Library/Preferences/com.apple.loginwindow HiddenUsersList \
    -array-add _fetchmail _dovecot
defaults write /Library/Preferences/com.apple.loginwindow HiddenUsersList \
    -array-add _fetchmail _dovenull
