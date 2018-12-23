@echo off
cd ../
python.exe source\scripts\packer.py -q -v build_data/GAME_VERSION.conf build_data/wotmods/ build/wotmods/
pause