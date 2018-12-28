@echo off
cd ..
if not exist ".\build\" mkdir .\build
if not exist ".\build\output\" mkdir .\build\output
if not exist ".\build\output\gen_conf\" mkdir .\build\output\gen_conf
echo Generating wotmods...
set log="build\output\gen_conf\wotmods.txt"
python source\scripts\generate_configs.py -d build_data/wotmods release/wotmods/ > %log%
type %log%
echo Generating wotmods_configs...
set log="build\output\gen_conf\wotmods_configs.txt"
python source\scripts\generate_configs.py -d build_data/wotmods release/wotmods_configs/ > %log%
type %log%
echo Generating archives...
set log="build\output\gen_conf\archives.txt"
python source\scripts\generate_configs.py -d build_data/archives release/archives/ > %log%
type %log%
echo Generating archives_configs...
set log="build\output\gen_conf\archives_configs.txt"
python source\scripts\generate_configs.py -d build_data/archives release/archives_configs/ > %log%
type %log%
pause
