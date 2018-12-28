@echo off
setlocal enabledelayedexpansion
cd ../../
python.exe source\scripts\compiler.py -d scripts/client/ -o build/scripts/client/ source/scripts/client/
