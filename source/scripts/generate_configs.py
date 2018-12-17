import json
import sys

import codecs
import os
import zipfile


def main():
    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'ld:')
    except getopt.error, msg:
        print msg
        print "usage: python %s [-l] [-d destdir] [-s sourcedir] [directory|file ...]" % os.path.basename(sys.argv[0])
        print
        print "arguments: one or more file and directory names to generate json for"
        print
        print "options:"
        print "-l: don't recurse into subdirectories"
        print "-d destdir: directory to write configs to"
        print "directory|file: place to pick archive(s) from"
        sys.exit(2)
    maxlevels = 10
    ddir = None
    for o, a in opts:
        if o == '-l': maxlevels = 0
        if o == '-d': ddir = a
    success = 1
    try:
        if args:
            for arg in args:
                if os.path.isdir(arg):
                    if not gen_dir(arg, maxlevels, ddir, arg):
                        success = 0
                else:
                    if not gen_file(arg, ddir, arg):
                        success = 0
        else:
            success = 1
    except KeyboardInterrupt:
        print "\n[interrupted]"
        success = 0
    return success


def gen_dir(path, maxlevels=10, ddir='', sdir=''):
    print 'Listing', path, '...'
    try:
        names = os.listdir(path)
    except os.error:
        print "Can't list", path
        names = []
    names.sort()
    success = 1
    for name in names:
        fullname = os.path.join(path, name).replace(os.sep, '/')
        if not os.path.isdir(fullname):
            if not gen_file(fullname, ddir, sdir):
                success = 0
        elif maxlevels > 0 and name != os.curdir and name != os.pardir and os.path.isdir(fullname) and not os.path.islink(
                fullname):
            if not gen_dir(fullname, maxlevels - 1, ddir, sdir):
                success = 0
    return success


def split_fully(path):  # we assume that zips can't have an empty folder/file name
    parts = path.split('/')
    return [part + '/' for part in parts[:-1] if part] + ([parts[-1]] if parts[-1] else [])


def fill_subdirs(data, parts):
    if parts:
        part = parts[0]
        subData = data.setdefault(part, {})
        if part.endswith('/'):
            fill_subdirs(subData, parts[1:])
        else:
            subData.update({'path': '', 'date': 'git', 'mode': 'file'})


def gen_file(fp, ddir, sdir):
    success = 1
    print 'Checking', fp, '...'
    name, ext = os.path.splitext(os.path.basename(fp))
    if ext not in ('.zip', '.wotmod'):
        return success
    file_data = {'ext': ext, 'files': {}}  # compression will depend on extension
    conf_name = os.path.join(ddir, os.path.dirname(fp), name + '.json').replace(os.sep, '/').replace(sdir, '')
    try:
        with zipfile.ZipFile(fp) as zf_orig:
            orig_infos_full = zf_orig.infolist()
            import re
            folder_ix_all = re.compile('mods/[.\d]*( Common Test)?/')
            for info in orig_infos_full:
                filename = info.filename
                if folder_ix_all.search(filename):
                    filename = folder_ix_all.sub('mods/{GAME_VERSION}/', filename)
                fill_subdirs(file_data['files'], split_fully(filename))
        conf_dir = os.path.dirname(conf_name)
        if not os.path.isdir(conf_dir):
            os.makedirs(conf_dir)
        with codecs.open(conf_name, 'w', 'utf-8-sig') as conf:
            json.dump(file_data, conf, sort_keys=True, indent=4, separators=(',', ': '), ensure_ascii=False, encoding='cp437')
    except StandardError, err:
        print err, sys.exc_info()[-1].tb_lineno
        print file_data
        success = 0
    return success


if __name__ == '__main__':
    exit_status = int(not main())
    sys.exit(exit_status)
