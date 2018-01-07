import binascii
import sys
import time
from datetime import datetime

import os
import zipfile


def main():
    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'lfqm:x:v:c:d:s:')
    except getopt.error, msg:
        print msg
        print "usage: python pack_wotmods.py [-l] [-f] [-q] [-m mode] [-x regexp] [-v version_str] [-c creation_date] [-d " \
              "destdir] [-s sourcedir] [directory|file ...]"
        print
        print "arguments: zero or more file and directory names to repack; if no arguments given,"
        print "           defaults to the equivalent of -l sys.path"
        print
        print "options:"
        print "-l: don't recurse into subdirectories"
        print "-f: force rebuild even if timestamps are up-to-date"
        print "-q: output only error messages"
        print "-m mode: 0 (ZIP_STORED) or 1 (ZIP_DEFLATED)"
        print "-x regexp: regular expression for files to match"
        print "-v version_str: versioned folder name. If given - all version-like folders (matching " \
              r'regex "mods/[.\d]*/") will be renamed to match "mods/version_str/".'
        print '-c creation_date: "%Y-%m-%d %H:%M:%S" - date of versioned folder creation.'
        print "-d destdir: directory to prepend to file paths for use in wotmod file"
        print "-s sourcedir: directory to pick files from"
        print "directory|file: place to pick wotmod(s) from"
        sys.exit(2)
    maxlevels = 10
    force = 0
    quiet = 0
    mode = zipfile.ZIP_STORED
    rx = None
    version_str = None
    date = None
    ddir = None
    sdir = None
    for o, a in opts:
        if o == '-l': maxlevels = 0
        if o == '-f': force = 1
        if o == '-q': quiet = 1
        if o == '-m': mode = zipfile.ZIP_STORED if not int(a) else zipfile.ZIP_DEFLATED
        if o == '-x':
            import re
            rx = re.compile(a)
        if o == '-v':
            import re
            if re.match(r'[.\d]*', a):
                version_str = a
        if o == '-c':
            date = datetime.strptime(a, '%Y-%m-%d %H:%M:%S').timetuple()[:6]
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
                    if not pack_dir(arg, maxlevels, sdir, ddir, version_str, date, rx, force, mode, quiet):
                        success = 0
                else:
                    if not pack_file(arg, sdir, ddir, version_str, date, rx, force, mode, quiet):
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


def pack_dir(dir, maxlevels=10, sdir=None, ddir=None, version_str=None, date=None, rx=None, force=0, mode=zipfile.ZIP_STORED,
             quiet=0):
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
        if not os.path.isdir(fullname):
            if not pack_file(fullname, sdir, ddir, version_str, date, rx, force, mode, quiet):
                success = 0
        elif maxlevels > 0 and name != os.curdir and name != os.pardir and os.path.isdir(fullname) and not os.path.islink(
                fullname):
            if not pack_dir(fullname, maxlevels - 1, sdir, ddir, version_str, date, rx, force, mode, quiet):
                success = 0
    return success


def pack_file(fullname, sdir=None, ddir=None, version_str=None, date=None, rx=None, force=0, mode=zipfile.ZIP_STORED,
              quiet=0):
    success = 1
    if rx is not None:
        mo = rx.search(fullname)
        if not mo:
            return success
    if not quiet:
        print 'Checking', fullname, '...'
    try:
        with zipfile.ZipFile(fullname) as zf_orig:
            orig_infos_full = zf_orig.infolist()
            orig_folder = ''
            if version_str:
                import re
                folder_rx = re.compile('mods/[.\d]*/$')
                folder_rx_all = re.compile('mods/[.\d]*/')
                for info in orig_infos_full:
                    if folder_rx_all.search(info.filename) and 'mods/%s/' % version_str not in info.filename:
                        search = folder_rx.search(info.filename)
                        if search:
                            info.date_time = date
                            orig_folder = search.group()
                            if quiet:
                                print 'Checking', fullname, '...'
                            print 'Updating versioned folder:', info.filename
                        info.filename = folder_rx_all.sub('mods/%s/' % version_str, info.filename)
            orig_infos = [x for x in orig_infos_full if
                          x.filename.startswith(ddir) and os.path.exists(x.filename.replace(ddir, sdir))]
            if not force and not orig_folder and all(
                    os.stat(x.filename.replace(ddir, sdir)).st_size == x.file_size for x in orig_infos if
                    not x.filename.endswith('/')):
                return success
            elif not orig_folder and quiet:
                print 'Checking', fullname, '...'
            orig_infos_noex = [x for x in orig_infos_full if x not in orig_infos]
            orig_datas_noex = [
                zf_orig.read(x.filename if not orig_folder else x.filename.replace('mods/%s/' % version_str, orig_folder))
                for x in orig_infos_noex]
        max_time = datetime(1970, 1, 1)
        with zipfile.ZipFile(fullname, 'w', mode) as zf_new:
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
                file_stamp = datetime.fromtimestamp(os.stat(file_name).st_mtime)
                if binascii.crc32(file_data) & 0xFFFFFFFF == info.CRC:
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
