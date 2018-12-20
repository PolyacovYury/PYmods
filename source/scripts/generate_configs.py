import sys

import codecs
import glob
import json
import os
import traceback
import zipfile


def main():
    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'ld:')
    except getopt.error, msg:
        print msg
        print "usage: python %s [-l] [-d destdir] [directory|file ...]" % os.path.basename(sys.argv[0])
        print '''   arguments: one or more file and directory names to generate json for
    options:
        -l: don't recurse into subdirectories
        -d destdir: directory to write configs to
        directory|file: place to pick archive(s) from'''
        sys.exit(2)
    max_levels = 10
    d_dir = None
    for o, a in opts:
        if o == '-l': max_levels = 0
        if o == '-d': d_dir = a
    success = True
    try:
        if args:
            for arg in args:
                if os.path.isdir(arg):
                    success &= gen_dir(arg, max_levels, d_dir, arg)
                else:
                    success &= gen_file(arg, d_dir, arg)
        else:
            success = False
    except KeyboardInterrupt:
        print "\n[interrupted]"
        success = False
    return success


def gen_dir(path, max_levels=10, d_dir='', s_dir=''):
    print 'Listing', path, '...'
    try:
        names = os.listdir(path)
    except os.error:
        print "Can't list", path
        names = []
    success = True
    for name in sorted(names):
        f_name = os.path.join(path, name).replace(os.sep, '/')
        if not os.path.isdir(f_name):
            success &= gen_file(f_name, d_dir, s_dir)
        elif max_levels > 0 and name not in (os.curdir, os.pardir) and os.path.isdir(f_name) and not os.path.islink(f_name):
            success &= gen_dir(f_name, max_levels - 1, d_dir, s_dir)
    return success


def find_file_path(arc_name, ext, f_path):
    path = ''
    f_name_full = os.path.basename(f_path)
    f_name, f_ext = os.path.splitext(f_name_full)
    if ext == '.zip':
        if '{' in f_name_full:
            api_files = glob.glob('res/wotmods/*%s*' % f_name_full.strip('{}'))
            if api_files:
                if len(api_files) == 1:  # WARNING! This means that this script has to be rerun if any of the APIs changes!
                    path = api_files[0].replace(os.sep, '/')
                else:
                    print 'Multiple fnmatches for file', f_path
        elif f_ext == '.wotmod':
            prefix, path = f_path.split('mods/{GAME_VERSION}/', 1)
            path = 'build/wotmods/' + '/'.join((os.path.dirname(path), (prefix or f_name).strip('/') + f_ext)).strip('/')
        elif 'mods/configs/' in f_path:
            path = 'res/configs/' + f_path.split('mods/configs/', 1)[1]
        elif f_ext in ('.png', '.jpg', '.txt'):
            path = 'res/img/%s/%s' % (arc_name, f_path)
        if path and os.path.isfile(path):
            return path
    elif ext == '.wotmod':
        if f_name_full == 'meta.xml':
            path = 'res/meta/%s.xml' % arc_name
        elif f_ext == '.pyc':
            path = f_path.replace('res/', 'build/')
        elif f_ext == '.swf':
            path = os.path.join('res/flash/', f_name_full).replace(os.sep, '/')
        elif f_ext == '.bnk':
            for attempt in ('/' + arc_name + '/', '/'):
                at_path = 'res/' + attempt.join(os.path.split(f_path))
                if os.path.isfile(at_path):
                    path = at_path
                    break
        elif f_ext in ('.png', '.model', '.primitives', '.primitives_processed', '.visual', '.visual_processed', '.vt',
                       '.dds', '.xml', '.track', '.texformat'):
            path = 'res/' + f_path
        if path and os.path.isfile(path):
            return path
    else:
        print 'Unknown archive extension:', ext
    print 'Source file not found for', f_path, 'in', path
    if path:
        print glob.glob(path.split()[0] + '*')
    return ''


def gen_file(fp, ddir, sdir):
    success = True
    print 'Checking', fp, '...'
    name, ext = os.path.splitext(os.path.basename(fp))
    if ext not in ('.zip', '.wotmod'):
        print 'Unknown archive extension:', ext
        return False
    file_data = {'enabled': True, 'ext': ext, 'files': {}}  # compression will depend on extension
    conf_name = os.path.join(ddir, os.path.dirname(fp), name + '.json').replace(os.sep, '/').replace(sdir, '')
    try:
        with zipfile.ZipFile(fp) as zf_orig:
            import re
            folder_ix_all = re.compile('mods/[.\d]*( Common Test)?/')
            paths = sorted(x.decode('cp866').encode('cp1251') for x in zf_orig.namelist())
            for idx, filename in enumerate(paths):
                filename = filename
                if not filename.endswith('/'):
                    if folder_ix_all.search(filename):
                        filename = folder_ix_all.sub('mods/{GAME_VERSION}/', filename)
                    for api_type in ('vxSettingsApi', 'vxBattleFlash', 'modslistapi'):
                        if api_type in os.path.basename(filename):
                            filename = '%s/{%s}' % (os.path.dirname(filename), api_type)
                    path = find_file_path(name, ext, filename)
                    if path:
                        file_data['files'].setdefault(filename, path)
                elif idx == (len(paths) - 1) or filename not in paths[idx + 1]:  # empty folder encountered
                    file_data['files'].setdefault(filename, '')
        conf_dir = os.path.dirname(conf_name)
        if not os.path.isdir(conf_dir):
            os.makedirs(conf_dir)
        with codecs.open(conf_name, 'w', 'utf-8-sig') as conf:
            json.dump(file_data, conf, sort_keys=True, indent=4, separators=(',', ': '), ensure_ascii=False,
                      encoding='cp1251')
    except StandardError:
        print traceback.format_exc()
        print file_data
        success = False
    return success


if __name__ == '__main__':
    exit_status = int(not main())
    sys.exit(exit_status)
