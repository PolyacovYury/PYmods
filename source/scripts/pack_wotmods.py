import binascii
import os
import sys
import time
import zipfile
from datetime import datetime


def main():
    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'lqd:s:')
    except getopt.error, msg:
        print msg
        print "usage: python pack_wotmods.py [-l] [-q] [-d destdir] [-s sourcedir] [directory|file ...]"
        print
        print "arguments: zero or more file and directory names to repack; if no arguments given,"
        print "           defaults to the equivalent of -l sys.path"
        print
        print "options:"
        print "-l: don't recurse into subdirectories"
        print "-q: output only error messages"
        print "-d destdir: directory to prepend to file paths for use in wotmod file"
        print "-s sourcedir: directory to pick files from"
        sys.exit(2)
    maxlevels = 10
    quiet = 0
    ddir = None
    sdir = None
    for o, a in opts:
        if o == '-l': maxlevels = 0
        if o == '-q': quiet = 1
        if o == '-d': ddir = a
        if o == '-s': sdir = a
    if ddir:
        if len(args) != 1 and not os.path.isdir(args[0]):
            print "-d destdir and -s sourcedir require exactly one directory argument"
            sys.exit(2)
    success = 1
    try:
        if args:
            for arg in args:
                if os.path.isdir(arg):
                    if not pack_dir(arg, maxlevels, sdir, ddir, quiet):
                        success = 0
                else:
                    if not pack_file(arg, sdir, ddir, quiet):
                        success = 0
        else:
            success = pack_path()
    except KeyboardInterrupt:
        print "\n[interrupted]"
        success = 0
    return success


def pack_path(skip_curdir=1, maxlevels=0, quiet=0):
    """Pack all wotmods on sys.path.

    Arguments (all optional):

    skip_curdir: if true, skip current directory (default true)
    maxlevels:   max recursion level (default 0)
    quiet: as for pack_dir() (default 0)
    """
    success = 1
    for dir in sys.path:
        if (not dir or dir == os.curdir) and skip_curdir:
            print 'Skipping current directory'
        else:
            success = success and pack_dir(dir, maxlevels, quiet=quiet)
    return success


def pack_dir(dir, maxlevels=10, sdir=None, ddir=None, quiet=0):
    """Pack all files in the given directory tree.

    Arguments (only dir is required):

    dir:       the directory to pick wotmods from
    maxlevels: maximum recursion level (default 10)
    sdir:      the directory that the files will be picked from
    ddir:      the directory that will be prepended to the path to the
               file as it is packed.
    quiet:     if 1, be quiet during packing
    """
    if not quiet:
        print 'Listing', dir, '...'
    try:
        names = os.listdir(dir)
    except os.error:
        print "Can't list", dir
        names = []
    names.sort()
    success = 1
    for name in names:
        fullname = os.path.join(dir, name).replace(os.sep, '/')
        if ddir is not None:
            dfile = os.path.join(ddir, name).replace(os.sep, '/')
        else:
            dfile = None
        if not os.path.isdir(fullname):
            if not pack_file(fullname, sdir, ddir, quiet):
                success = 0
        elif maxlevels > 0 and name != os.curdir and name != os.pardir and os.path.isdir(fullname) and not os.path.islink(
                fullname):
            if not pack_dir(fullname, maxlevels - 1, sdir, dfile, quiet):
                success = 0
    return success


def pack_file(fullname, sdir=None, ddir=None, quiet=0):
    success = 1
    if not fullname.endswith('.wotmod'):
        return success
    if not quiet:
        print 'Checking', fullname, '...'
    try:
        with zipfile.ZipFile(fullname) as zf_orig:
            orig_names_full = zf_orig.namelist()
            orig_names = [x for x in orig_names_full if x.startswith(ddir) and os.path.exists(x.replace(ddir, sdir))]
            orig_infos = [zf_orig.getinfo(x) for x in orig_names]
            orig_names_noex = [x for x in orig_names_full if x not in orig_names]
            orig_infos_noex = [zf_orig.getinfo(x) for x in orig_names_noex]
            orig_datas_noex = [zf_orig.read(x) for x in orig_names_noex]
        max_time = datetime(1970, 1, 1)
        with zipfile.ZipFile(fullname, 'w') as zf_new:
            for info, data in zip(orig_infos_noex, orig_datas_noex):
                max_time = max(max_time, datetime(*info.date_time))
                zf_new.writestr(info, data)
            for info in orig_infos:
                file_name = info.filename.replace(ddir, sdir)
                if os.path.isdir(file_name):
                    file_data = ''
                else:
                    with open(file_name, 'rb') as fin:
                        file_data = fin.read()
                file_crc = binascii.crc32(file_data) & 0xFFFFFFFF
                file_stat = os.stat(file_name)
                file_stamp = datetime.fromtimestamp(file_stat.st_mtime)
                if file_crc == info.CRC:
                    info.date_time = min(datetime(*info.date_time), file_stamp).timetuple()[:6]
                else:
                    info.date_time = file_stamp.timetuple()[:6]
                    print 'Updating file', info.filename
                max_time = max(max_time, datetime(*info.date_time))
                zf_new.writestr(info, file_data)
        os.utime(fullname, (time.time(), time.mktime(max_time.timetuple())))
    except StandardError, err:
        print err, sys.exc_info()[-1].tb_lineno
        success = 0
    return success


if __name__ == '__main__':
    exit_status = int(not main())
    sys.exit(exit_status)
