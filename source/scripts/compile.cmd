@echo off
setlocal enabledelayedexpansion
cd ../../
python.exe source\scripts\gitcompileall.py -d scripts/client/ source/scripts/client/
