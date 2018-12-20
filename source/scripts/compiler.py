import __builtin__
import imp
import marshal
import os
import py_compile
import struct
import subprocess
import sys
import time


def get_git_date(path):
    return subprocess.check_output('git --no-pager log -n 1 --format="%ct" --'.split() + [path])[1:-2]


def compile_dir(path, max_levels=10, d_dir=None, o_dir=None, force=False, quiet=False):
    if not quiet:
        print 'Listing', path, '...'
    try:
        names = os.listdir(path)
    except os.error:
        print "Can't list", path
        names = []
    success = True
    for name in sorted(names):
        f_name = os.path.join(path, name).replace(os.sep, '/')
        d_file = None if d_dir is None else os.path.join(d_dir, name).replace(os.sep, '/')
        o_file = None if o_dir is None else os.path.join(o_dir, name).replace(os.sep, '/')
        if not os.path.isdir(f_name):
            success &= compile_file(f_name, d_file, o_file, force, quiet)
        elif max_levels > 0 and name not in (os.curdir, os.pardir) and os.path.isdir(f_name) and not os.path.islink(f_name):
            success &= compile_dir(f_name, max_levels - 1, d_file, o_file, force, quiet)
    return success


def compile_file(fullname, d_file=None, o_file=None, force=False, quiet=False):
    success = True
    name = os.path.basename(fullname)
    head, tail = name[:-3], name[-3:]
    if not os.path.isfile(fullname) or tail != '.py':
        return success
    timeStr = get_git_date(fullname)
    if not force and head != '__init__':
        try:
            m_time = int(timeStr) if timeStr else int(os.stat(fullname).st_mtime)
            expect = struct.pack('<4sl', imp.get_magic(), m_time)
            c_file = (o_file or fullname) + (__debug__ and 'c' or 'o')
            with open(c_file, 'rb') as c_handle:
                actual = c_handle.read(8)
            if expect == actual:
                return success
        except IOError:
            pass
    if not quiet:
        print 'Compiling', fullname, '...'
    try:
        ok = do_compile(fullname, d_file, o_file, True, timeStr)
    except py_compile.PyCompileError, err:
        if quiet:
            print 'Compiling', fullname, '...'
        print err.msg
        success = False
    except IOError, e:
        print "Sorry", e
        success = False
    else:
        success &= ok
    return success


def main():
    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'lfqd:o:')
    except getopt.error, msg:
        print msg
        print "usage: python %s [-l] [-f] [-q] [-d dest_dir] [-o output_dir] [directory|file ...]" % os.path.basename(
            sys.argv[0])
        print '''    arguments: one or more file and directory names to compile
    options:
        -l: don't recurse into subdirectories
        -f: force rebuild even if timestamps are up-to-date
        -q: output only error messages
        -d dest_dir: directory to prepend to file paths for use in compile-time tracebacks and
            in runtime tracebacks in cases where the source file is unavailable
        -o output_dir: directory to put compiled files into, defaults to the folder being compiled'''
        sys.exit(2)
    max_levels = 10
    d_dir = None
    o_dir = None
    force = 0
    quiet = 0
    for o, a in opts:
        if o == '-l': max_levels = 0
        if o == '-f': force = True
        if o == '-q': quiet = True
        if o == '-d': d_dir = a
        if o == '-o': o_dir = a
    if o_dir:
        if len(args) != 1 and not os.path.isdir(args[0]):
            print "-o output_dir requires exactly one directory argument"
            sys.exit(2)
    success = True
    try:
        if args:
            for arg in args:
                if os.path.isdir(arg):
                    success &= compile_dir(arg, max_levels, d_dir, o_dir, force, quiet)
                else:
                    success &= compile_file(arg, d_dir, o_dir, force, quiet)
        else:
            print 'One or more arguments required to compile'
            success = False
    except KeyboardInterrupt:
        print "\n[interrupted]"
        success = 0
    return success


def do_compile(f_path, d_file=None, o_file=None, raises=False, timeStr=''):
    with open(f_path, 'U') as f:
        if timeStr:
            maxTS = timestamp = long(timeStr)
        else:
            try:
                maxTS = timestamp = long(os.fstat(f.fileno()).st_mtime)
            except AttributeError:
                maxTS = timestamp = long(os.stat(f_path).st_mtime)
        codestring = f.read()
    modName = f_path
    if '__init__' in f_path:
        modName = os.path.dirname(f_path)
        if '%(file_compile_date)s' in codestring:
            timeStr = get_git_date(modName)
            if not timeStr:
                print 'Non-versioned mod folder detected:', modName
                for path in ('/'.join((x[0], y)).replace(os.sep, '/') for x in os.walk(modName) for y in x[2]):
                    if not path.endswith('.py'):
                        continue
                    timeStr = get_git_date(path)
                    m_time = long(timeStr) if timeStr else long(os.stat(path).st_mtime)
                    if m_time > maxTS:
                        maxTS = m_time
            else:
                maxTS = long(timeStr)  # if __init__ is the newest - it will be reflected in folder's commit date
    codestring = codestring.replace('%(file_compile_date)s', time.strftime('%d.%m.%Y', time.localtime(maxTS))).replace(
        '%(mod_ID)s', os.path.basename(modName).replace('.py', '').replace('mod_', ''))
    try:
        code_object = __builtin__.compile(codestring, d_file or f_path, 'exec')
    except Exception, err:
        py_exc = py_compile.PyCompileError(err.__class__, err, d_file or f_path)
        if raises:
            raise py_exc
        else:
            sys.stderr.write(py_exc.msg + '\n')
            return False
    o_file = (o_file or f_path) + (__debug__ and 'c' or 'o')
    o_dir = os.path.dirname(o_file)
    if not os.path.isdir(o_dir):
        os.makedirs(o_dir)
    with open(o_file, 'wb') as fc:
        fc.write('\0\0\0\0')
        py_compile.wr_long(fc, timestamp)
        marshal.dump(code_object, fc)
        fc.flush()
        fc.seek(0, 0)
        fc.write(py_compile.MAGIC)
    if timeStr:
        os.utime(o_file, (time.time(), timestamp))
    return True


if __name__ == '__main__':
    exit_status = int(not main())
    sys.exit(exit_status)
