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
        return long(timestamp), filename
    except ValueError:
        return None, line


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
                if timestamp is not None and '.mtimes' not in filename:
                    data[filename] = timestamp
    return data


def update_data(path, data, rec):
    rem = path
    filesList = subprocess.check_output(['git', 'ls-files', path + '/']).split('\n')
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
                x = x.encode('cp1251')
                if os.path.isfile(x):
                    data[act_path] = int(os.stat(x).st_mtime)


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
            for filename in data.keys():
                f_path = os.path.join(os.path.dirname(path), filename)
                if os.path.isfile(f_path):
                    change_date(data[filename], f_path)
                else:
                    print 'Deleted file detected:', f_path.replace('\\', '/')
                    del data[filename]
            if path:
                write(path, data)
    elif mode in 'as':
        print 'Saving modification dates'
        for path in subprocess.check_output(['git', 'ls-files', '*.mtimes*']).split('\n'):
            if not path:
                return
            data = mode == 's' and parse_file(path) or {}
            update_data(os.path.dirname(path) or '.', data, path.endswith('r'))
            write(path, data)
    else:
        print 'Unknown mode:', mode
        help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
