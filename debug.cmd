@echo off
:::git checkout develop
python.exe source\scripts\gitcompileall.py -d scripts/client/ source/scripts/client/
python.exe source\scripts\pack_wotmods.py -q -m 0 -i .*.wotmod$ -e .*pol.* -d res/scripts/client/ -s source/scripts/client/ release/wotmods
echo Launching Beyond Compare...
"C:\Program Files\Beyond Compare 4\BCompare.exe" release\wotmods\ "D:\Games\World_of_Tanks\mods\1.3.0.1\" /solo
echo Exiting.
pause
exit