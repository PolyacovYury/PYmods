import codecs
import glob
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from datetime import datetime

folder_ix_all = re.compile('mods/[.\d]*( Common Test)?/')
printed = False


def pack_dir(path, o_dir, max_levels=10, v_str=None, v_date=None, force=False, quiet=False):
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
        o_file = os.path.join(o_dir, name).replace(os.sep, '/')
        if not os.path.isdir(f_name):
            success &= pack_file(f_name, o_file, v_str, v_date, force, quiet)
        elif max_levels > 0 and name not in (os.curdir, os.pardir) and os.path.isdir(f_name) and not os.path.islink(f_name):
            success &= pack_dir(f_name, o_file, max_levels - 1, v_str, v_date, force, quiet)
    return success


def ch_print(path, quiet, *args):
    global printed
    if quiet and not printed:
        print 'Checking', path, '...'
        printed = True
    if args:
        print ' '.join(args)


def pack_file(conf_name, out_path, v_str=None, v_date=None, force=False, quiet=False):
    global printed
    printed = False
    if not quiet:
        ch_print(conf_name, True)
    with codecs.open(conf_name, 'r', 'utf-8-sig') as fp:
        data = json.load(fp, 'utf-8-sig')
    if not data['enabled']:
        ch_print(conf_name, quiet, 'Archive disabled.')
        return True
    if any('{GAME_VERSION}' in path for path in data['files']) and v_str is None:
        ch_print(conf_name, quiet, 'Encountered an archive which requires game version data, but it was not provided.')
        sys.exit(2)
    new_ext = data['ext']
    if new_ext == '.zip':
        mode = zipfile.ZIP_DEFLATED
    elif new_ext == '.wotmod':
        mode = zipfile.ZIP_STORED
    else:
        ch_print(conf_name, quiet, 'Unknown extension:', new_ext)
        return False
    out_path = os.path.splitext(out_path)[0].decode('cp1251') + new_ext
    if os.path.isfile(out_path):
        if not force and check_identical(out_path, data['files'], v_str, quiet):
            return True
    else:
        ch_print(out_path, quiet, 'Output file not found, creating a new one...')
    return do_pack(out_path, data['files'], mode, v_str, v_date)


def compute_names(fp, paths, v_str, quiet):
    file_names = {}
    mismatched = []
    for idx, filename in enumerate(paths):
        if not filename.endswith('/') or (idx == (len(paths) - 1) or filename not in paths[idx + 1]):
            new = ''
            search = folder_ix_all.search(filename)
            if search:
                ver_dir = search.group()
                file_ver = ver_dir.replace('mods', '').strip('/')
                if file_ver != v_str:
                    mismatch = filename[:search.end()]
                    if mismatch not in mismatched:
                        mismatched.append(mismatch)
                        ch_print(fp, quiet, 'Updating versioned folder:', mismatch)
                new = folder_ix_all.sub('mods/{GAME_VERSION}/', filename)
            for api_type in ('vxSettingsApi', 'vxBattleFlash', 'modslistapi'):
                if api_type in os.path.basename(filename):
                    file_names['%s/*%s*' % (os.path.dirname(new or filename), api_type)] = filename
                    break
            else:
                file_names[new or filename] = filename
    return file_names, mismatched


def get_stat_size_time(path):
    stat = os.stat(path)
    stat_date = datetime.fromtimestamp(stat.st_mtime)
    stat_date = stat_date.replace(second=stat_date.second / 2 * 2)
    return stat.st_size, stat_date.timetuple()[:6]


def check_identical(fp, arc_data, v_str, quiet=False):
    identical = True
    with zipfile.ZipFile(fp) as zf_orig:
        paths = sorted(x.decode('cp866') for x in zf_orig.namelist())
        act_data, mismatched = compute_names(fp, paths, v_str, quiet)
        if mismatched or sorted(act_data) != sorted(arc_data):
            identical = False
        for f_path in sorted(arc_data):
            if f_path.endswith('/'):  # empty folder
                if f_path not in act_data:
                    ch_print(fp, quiet, 'Adding missing folder:', f_path)
            else:
                if f_path in act_data:
                    act_path = act_data[f_path] or f_path
                    info = zf_orig.getinfo(act_path.encode('cp866'))
                    files = [p.replace(os.sep, '/') for p in glob.iglob(arc_data[f_path])]
                    if files:
                        if len(files) > 1:
                            ch_print(fp, quiet, 'Ambiguous wildcard:', arc_data[f_path], 'picked file:', files[0],
                                     'other matches:', files[1:])
                        act_path = files[0]
                    else:
                        ch_print(fp, quiet, 'Could not find file:', arc_data[f_path])
                        continue
                    if (info.file_size, info.date_time) != get_stat_size_time(act_path):
                        identical = False
                        ch_print(fp, quiet, 'Updating file', info.filename)
                else:
                    ch_print(fp, quiet, 'Adding missing file:', f_path)
        for f_path in sorted(act_data):
            if f_path not in arc_data:
                ch_print(fp, quiet, 'Deleting file:', f_path)
    return identical


def make_tree(paths):
    tree = {}
    for path in paths:
        sub = tree
        dirs = path.split('/')
        for x in dirs[:-1]:
            if x:
                sub = sub.setdefault(x + '/', {})
        if dirs[-1]:
            sub.setdefault(dirs[-1], '')
    return tree


def pack_stuff(zf_new, mode, tree, arc_data, v_str, v_date, v_was, cur_path):
    min_time, max_time = datetime.fromtimestamp(time.time()), datetime(1970, 1, 1)
    for sub_name, sub_data in sorted(tree.iteritems(), key=lambda i: (isinstance(i[1], dict), not bool(i[1]), i[0])):
        sub_path = sub_name if not cur_path else cur_path + sub_name
        if isinstance(sub_data, dict):
            if sub_data:  # non-empty folder
                packed = pack_stuff(zf_new, mode, sub_data, arc_data, v_str, v_date, v_was, sub_path)
                min_time = min(min_time, packed[0])
                max_time = max(max_time, packed[1])
                v_was |= packed[2]
            else:
                zf_new.writestr(zipfile.ZipInfo(sub_path, min_time.timetuple()[:6]), '', mode)
        else:
            path = glob.glob(arc_data[sub_path])[0].replace(os.sep, '/')
            with open(path, 'rb') as f:
                st_time = get_stat_size_time(path)[1]
                min_time = min(min_time, datetime(*st_time))
                max_time = max(max_time, datetime(*st_time))
                path = sub_path if '*' not in sub_path else os.path.dirname(sub_path) + '/' + os.path.basename(path)
                if isinstance(path, unicode):
                    path = path.encode('cp866')
                if v_str is not None:
                    if path.endswith('{GAME_VERSION}/'):
                        st_time = v_date.timetuple()[:6]
                        v_was = True
                    path = path.replace('{GAME_VERSION}', v_str)
                zf_new.writestr(zipfile.ZipInfo(path, st_time), f.read(), mode)
    if cur_path:
        zf_new.writestr(zipfile.ZipInfo(cur_path, min_time.timetuple()[:6]), '', mode)
    return min_time, max_time, v_was


def do_pack(fp, arc_data, mode, v_str, v_date):
    fd = os.path.dirname(fp)
    if not os.path.isdir(fd):
        os.makedirs(fd)
    tree = make_tree(sorted(arc_data))
    with zipfile.ZipFile(fp, 'w', mode) as zf_new:
        min_time, max_time, v_was = pack_stuff(zf_new, mode, tree, arc_data, v_str, v_date, False, '')
    if v_str is not None and v_was:
        max_time = max(max_time, v_date)
    os.utime(fp, (time.time(), time.mktime(max_time.timetuple())))
    return True


def main():
    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'lfqv:')
    except getopt.error, msg:
        print msg
        print "usage: python %s [-l] [-f] [-q] [-v version_file] configs_dir output_dir" % os.path.basename(sys.argv[0])
        print '''    arguments:
        configs_dir: directory to pick configs from
        output_dir: directory to place built archives into
    options:
        -l: don't recurse into subdirectories
        -f: force rebuild even if timestamps are up-to-date
        -q: output only error messages and archive update reasons 
        -v version_file: if a {GAME_VERSION} macro is encountered and this path is not provided - build will fail'''
        sys.exit(2)
    max_levels = 10
    force = False
    quiet = False
    version_file = None
    for o, a in opts:
        if o == '-l': max_levels = 0
        if o == '-f': force = True
        if o == '-q': quiet = True
        if o == '-v': version_file = a
    if len(args) != 2:
        print 'packer only needs to know where to pick configs from and where to put the results to'
        sys.exit(2)
    success = True
    version_str = None
    version_date = None
    if version_file:
        try:
            with open(version_file, 'r') as v_file:
                version_str = v_file.read().strip()
            assert version_str
            timeStr = subprocess.check_output('git --no-pager log -n 1 --format="%ct" --'.split() + [version_file])[1:-2]
            version_date = datetime.fromtimestamp(long(timeStr) if timeStr else long(os.stat(version_file).st_mtime))
        except IOError:
            print 'WARNING: version file not found:', version_file
        except AssertionError:
            print 'WARNING: version was empty'
            version_str = None
    else:
        print 'WARNING: version file not provided'
    try:
        if os.path.exists(args[0]):
            if os.path.isdir(args[0]):
                success &= pack_dir(args[0], args[1], max_levels, version_str, version_date, force, quiet)
            else:
                success &= pack_file(args[0], args[1], version_str, version_date, force, quiet)
        else:
            print 'Build config file/directory not found'
            success = False
    except KeyboardInterrupt:
        print "\n[interrupted]"
        success = False
    return success


if __name__ == '__main__':
    sys.exit(int(not main()))
