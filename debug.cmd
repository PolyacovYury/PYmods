@echo off
:::git checkout develop
python.exe source\scripts\compiler.py -d scripts/client/ -o build/scripts/client/ source/scripts/client/
python.exe source\scripts\packer.py -q -v build_data/GAME_VERSION.conf build_data/wotmods/ build/wotmods/
echo Launching Beyond Compare...
set /p ver=<build_data\GAME_VERSION.conf
"C:\Program Files\Beyond Compare 4\BCompare.exe" build\wotmods\ "D:\Games\World_of_Tanks\mods\%ver%\" /solo
echo Exiting.
pause
exit
