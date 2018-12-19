"""
https://github.com/kareltucek/git-mtime-extension/
Pythonized and repurposed by Polyacov_Yury
"""
import sys

import codecs
import os
import subprocess


def change_date(timestamp, filename):
    stat = os.stat(filename)
    os.utime(filename, (stat.st_atime, timestamp))


def parse_line(line):
    try:
        timestamp, filename = line.split('|')
        return int(timestamp), filename
    except ValueError:
        return 0, line  # there will never be a file with exactly 0 timestamp


def help():
    print '''version: 1.6
    usage: mtimestore <switch>
    options:
      -a  saves mtimes of all git-versed files into .mtimes file (done on intialization of mtime fixes)
      -s  saves mtimes of modified staged files into .mtimes file(pre-commit hook)
      -r  restores mtimes from .mtimes file (stored in repository server-side, called in post-checkout hook)
      -h  show this help'''


def parse_file(path):
    data = {}
    if os.path.isfile(path):
        with codecs.open(path, 'r', 'utf-8-sig') as fstream:
            for line in fstream.read().split('\n'):
                line = line.strip()
                if not line: continue
                timestamp, filename = parse_line(line)
                if timestamp and '.mtimes' not in filename:
                    data[filename] = timestamp
    return data


def update_data(root, path, data, a, rec):
    if a:
        rem = path
        filesList = subprocess.check_output(['git', 'ls-files', path + '/']).split('\n')
    else:
        rem = os.path.join(root, path)
        filesList = [(x if not root or not x.startswith(root) else x.split(root, 1)[1]) for x in
                     subprocess.check_output(['git', 'diff', '--name-only', '--staged', path + '/']).split('\n')]
    rem = rem if not rem or rem.endswith('/') else rem + '/'
    for act_path in data.keys():
        x = rem + act_path
        if not os.path.isfile(x.encode('cp1251')):
            data.pop(act_path)
    for x in filesList:
        x = x.strip().strip('"').decode('string-escape').decode('utf8')
        if x and '.mtimes' not in x:
            act_path = x if not rem or not x.startswith(rem) else x.split(rem, 1)[1]
            if rec or '/' not in act_path:
                data[act_path] = int(os.stat(x.encode('cp1251')).st_mtime)


def write(path, data):
    with codecs.open(path, 'w', 'utf-8-sig') as fstream:
        for filename in sorted(data):
            if filename:
                fstream.write('%s|%s\n' % (data[filename], filename))


def main():
    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'aAsr')
    except getopt.error, msg:
        print msg
        help()
        sys.exit(2)
    if args:
        print 'Unexpected arguments:', args
        sys.exit(2)
    if len(opts) > 1:
        print 'Only one argument expected, got several:', [o for o, _ in opts]
        help()
        sys.exit(2)
    mode = opts[0][0].strip('-')
    if mode == 'r':
        print 'Restoring modification dates'
        for path in subprocess.check_output(['git', 'ls-files', '*.mtimes*']).split('\n'):
            data = parse_file(path)
            for filename in data:
                change_date(data[filename], os.path.join(os.path.dirname(path), filename))
    elif mode in 'as':
        print 'Saving modification dates'
        for path in subprocess.check_output(['git', 'ls-files', '*.mtimes*']).split('\n'):
            if not path:
                return
            data = mode == 'a' and parse_file(path) or {}
            update_data(subprocess.check_output('git rev-parse --show-prefix'.split()).strip(), os.path.dirname(path) or '.',
                        data, mode == 'a', path.endswith('r'))
            write(path, data)
    else:
        print 'Unknown mode:', mode
        help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
