@echo off
py -2 source/scripts/compile/packer.py -q -v build_data/GAME_VERSION.conf build_data/archives/ build/archives/
echo Launching Beyond Compare...
start "" "BCompare.exe" build\archives\ "E:\Files\YandexDisk\PYmods\"
start "" "BCompare.exe" build\archives\ "E:\Files\Google Drive\PYmods\"
echo Exiting.
pause
exit
