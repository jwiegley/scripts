#!/bin/bash

hdiutil attach /Applications/Install\ macOS\ Sierra.app/Contents/SharedSupport/InstallESD.dmg \
        -noverify -nobrowse -mountpoint /Volumes/install_app
hdiutil create -o /tmp/Sierra.cdr -size 7316m -layout SPUD -fs HFS+J
hdiutil attach /tmp/Sierra.cdr.dmg -noverify -nobrowse -mountpoint /Volumes/install_build
asr restore -source /Volumes/install_app/BaseSystem.dmg \
    -target /Volumes/install_build -noprompt -noverify -erase
rm /Volumes/OS\ X\ Base\ System/System/Installation/Packages
cp -rp /Volumes/install_app/Packages /Volumes/OS\ X\ Base\ System/System/Installation/
cp -rp /Volumes/install_app/BaseSystem.chunklist /Volumes/OS\ X\ Base\ System/BaseSystem.chunklist
cp -rp /Volumes/install_app/BaseSystem.dmg /Volumes/OS\ X\ Base\ System/BaseSystem.dmg
hdiutil detach /Volumes/install_app
hdiutil detach /Volumes/OS\ X\ Base\ System/
hdiutil convert /tmp/Sierra.cdr.dmg -format UDTO -o /tmp/Sierra.iso
mv /tmp/Sierra.iso.cdr ~/dl/Sierra.iso
