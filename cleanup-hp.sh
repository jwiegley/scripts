#!/bin/sh

rm -fr /Applications/Hewlett-Packard

rm -fr /Library/Receipts/HP*
rm -fr "/Library/PreferencePanes/HP Scanners.prefPane"
rm -fr "/Library/Image Capture/TWAIN Data Sources/HPScanPro.ds"
rm -fr "/Library/Documentation/Help/Hewlett-Packard"
rm -fr "/Library/Application Support/Hewlett-Packard"

rm -fr "/System/Library/Extensions/hpPlugInInit.kext"

touch /System/Library/Extensions.mkext
touch /System/Library/Extensions/
touch /System/Library/Extensions/Caches/
