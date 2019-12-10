@echo off
py -2 source/scripts/compile/packer.py -q -v build_data/GAME_VERSION.conf build_data/archives/ build/archives/
echo Launching Beyond Compare...
"BCompare.exe" build\archives\ "D:\Юрино\YandexDisk\PYmods\"
echo Exiting.
pause
exit
