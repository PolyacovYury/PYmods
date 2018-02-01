import binascii
import sys
import time
from datetime import datetime

import os
import zipfile


def main():
    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'lfqm:i:e:v:c:w:d:s:')
    except getopt.error, msg:
        print msg
        print "usage: python pack_wotmods.py [-l] [-f] [-q] [-m mode] [-i regexp] [-e regexp] [-v version_str] " \
              "[-c creation_date] [-w wildcards] [-d destdir] [-s sourcedir] [directory|file ...]"
        print
        print "arguments: zero or more file and directory names to repack; if no arguments given,"
        print "           defaults to the equivalent of -l sys.path"
        print
        print "options:"
        print "-l: don't recurse into subdirectories"
        print "-f: force rebuild even if timestamps are up-to-date"
        print "-q: output only error messages"
        print "-m mode: 0 (ZIP_STORED) or 1 (ZIP_DEFLATED)"
        print "-i regexp: regular expression for files to include"
        print "-e regexp: regular expression for files to exclude"
        print "-v version_str: versioned folder name. If given - all version-like folders (matching " \
              r'regex "mods/[.\d]*/") will be renamed to match "mods/version_str/".'
        print '-c creation_date: "%Y-%m-%d %H:%M:%S" - date of versioned folder creation.'
        print '-w wildcards: wildcards for files to be identical in archive and in source folder, split by "|".' \
              ' case-insensitive.'
        print "-d destdir: directory to prepend to file paths for use in wotmod file"
        print "-s sourcedir: directory to pick files from"
        print "directory|file: place to pick wotmod(s) from"
        sys.exit(2)
    maxlevels = 10
    force = 0
    quiet = 0
    mode = zipfile.ZIP_STORED
    ix = None
    ex = None
    version_str = None
    date = None
    wc = None
    ddir = None
    sdir = None
    for o, a in opts:
        if o == '-l': maxlevels = 0
        if o == '-f': force = 1
        if o == '-q': quiet = 1
        if o == '-m': mode = zipfile.ZIP_STORED if not int(a) else zipfile.ZIP_DEFLATED
        if o == '-i':
            import re
            ix = re.compile(a)
        if o == '-e':
            import re
            ex = re.compile(a)
        if o == '-w':
            wc = a.split('|')
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
                    if not pack_dir(arg, maxlevels, sdir, ddir, version_str, date, ix, ex, wc, force, mode, quiet):
                        success = 0
                else:
                    if not pack_file(arg, sdir, ddir, version_str, date, ix, ex, wc, force, mode, quiet):
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


def pack_dir(dir, maxlevels=10, sdir=None, ddir=None, version_str=None, date=None, ix=None, ex=None, wc=None, force=0,
             mode=zipfile.ZIP_STORED,
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
            if not pack_file(fullname, sdir, ddir, version_str, date, ix, ex, wc, force, mode, quiet):
                success = 0
        elif maxlevels > 0 and name != os.curdir and name != os.pardir and os.path.isdir(fullname) and not os.path.islink(
                fullname):
            if not pack_dir(fullname, maxlevels - 1, sdir, ddir, version_str, date, ix, ex, wc, force, mode, quiet):
                success = 0
    return success


def pack_file(fullname, sdir=None, ddir=None, version_str=None, date=None, ix=None, ex=None, wc=None, force=0,
              mode=zipfile.ZIP_STORED, quiet=0):
    success = 1
    if ix is not None:
        if not ix.search(fullname):
            return success
    if ex is not None:
        if ex.search(fullname):
            return success
    if not quiet:
        print 'Checking', fullname, '...'
    try:
        with zipfile.ZipFile(fullname) as zf_orig:
            orig_infos_full = zf_orig.infolist()
            orig_folder = ''
            if version_str:
                import re
                folder_ix = re.compile('mods/[.\d]*/$')
                folder_ix_all = re.compile('mods/[.\d]*/')
                for info in orig_infos_full:
                    filename = info.filename
                    if folder_ix_all.search(filename) and 'mods/%s/' % version_str not in filename:
                        search = folder_ix.search(filename)
                        if search:
                            info.date_time = date
                            orig_folder = search.group()
                            if quiet:
                                print 'Checking', fullname, '...'
                            print 'Updating versioned folder:', filename
                        info.filename = folder_ix_all.sub('mods/%s/' % version_str, filename)
            replaced = {}
            if wc:
                import fnmatch
                import glob
                for card in wc:
                    for info in orig_infos_full:
                        dfile = info.filename
                        sfile = dfile.replace(ddir, sdir)
                        card_glob = [x.replace(os.sep, '/') for x in glob.iglob('%s/%s' % (os.path.dirname(sfile), card))]
                        if fnmatch.fnmatch(dfile, card) and not os.path.exists(sfile) and card_glob:
                            if len(card_glob) > 1:
                                print 'Ambiguous wildcard:', card, 'picked file:', card_glob[0], 'other matches:', \
                                    card_glob[1:]
                            if dfile in replaced.values():
                                print 'Intersecting wildcards match with file', dfile, 'detected at:', card
                            else:
                                new_file = card_glob[0].replace(sdir, ddir)
                                replaced[new_file] = dfile
                                info.filename = new_file
                                info.date_time = datetime.fromtimestamp(os.stat(card_glob[0]).st_mtime).timetuple()[:6]
            orig_infos = [x for x in orig_infos_full if x.filename in replaced or
                          x.filename.startswith(ddir) and os.path.exists(x.filename.replace(ddir, sdir))]
            if not force and not orig_folder and not replaced:
                identical = True
                for x in orig_infos:
                    if not x.filename.endswith('/'):
                        stat = os.stat(x.filename.replace(ddir, sdir))
                        stat_date = datetime.fromtimestamp(stat.st_mtime)
                        stat_date = stat_date.replace(second=stat_date.second / 2 * 2)
                        if stat.st_size != x.file_size or stat_date.timetuple()[:6] != x.date_time:
                            identical = False
                            break
                if identical:
                    return success
                elif quiet:
                    print 'Checking', fullname, '...'
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
                file_stamp = file_stamp.replace(second=file_stamp.second / 2 * 2)
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
