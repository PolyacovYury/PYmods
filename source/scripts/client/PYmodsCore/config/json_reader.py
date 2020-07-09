# coding=utf-8
import binascii
import zlib

import codecs
import json
import os
import re
import traceback
from collections import OrderedDict
from .utils import smart_update

__all__ = ['loadJson', 'loadJsonOrdered']


class JSONEncoder(json.JSONEncoder):
    def encode(self, o, i=0):
        try:  # Special Processing for lists
            dedent = ' ' * i
            i += self.indent
            indent = ' ' * i
            item_sep = '%s\n' % self.item_separator
            if isinstance(o, (list, tuple)):
                if not any(isinstance(x, dict) for x in o):
                    result = '[%s]' % ('%s ' % self.item_separator).join(self.encode(x) for x in o)
                    if len(result) <= 80:
                        return result
                return '[\n%s\n%s]' % (item_sep.join(indent + self.encode(x, i) for x in o), dedent)
            elif isinstance(o, dict):
                if not o:
                    return '{}'
                keys = o.keys()
                if self.sort_keys:
                    keys = sorted(keys)
                return '{\n%s\n%s}' % (item_sep.join(
                    '%s%s%s%s' % (indent, json.dumps(k), self.key_separator, self.encode(o[k], i)) for k in keys), dedent)
            else:
                return super(JSONEncoder, self).encode(o)
        except StandardError:
            traceback.print_exc()
            print type(o)
            return str(o)


class JSONLoader:
    @classmethod
    def byte_ify(cls, inputs, ignore_dicts=False):  # https://stackoverflow.com/a/33571117
        if isinstance(inputs, unicode):
            return inputs.encode('utf-8')
        elif isinstance(inputs, list):
            return [cls.byte_ify(element, ignore_dicts=True) for element in inputs]
        elif isinstance(inputs, tuple):
            return tuple(cls.byte_ify(element, ignore_dicts=True) for element in inputs)
        elif isinstance(inputs, OrderedDict):  # can't use object_hook and object_pairs_hook at the same time
            return OrderedDict((cls.byte_ify(key), cls.byte_ify(value)) for key, value in inputs.iteritems())
        elif isinstance(inputs, dict) and not ignore_dicts:
            return {cls.byte_ify(key, ignore_dicts=True): cls.byte_ify(value, ignore_dicts=True) for key, value in
                    inputs.iteritems()}
        return inputs

    @classmethod
    def stringed_ints(cls, inputs):
        if inputs and isinstance(inputs, dict):  # OrderedDict is a subclass of dict
            gen_expr = (
                ((str(key) if isinstance(key, int) else key), cls.stringed_ints(value)) for key, value in inputs.iteritems())
            if isinstance(inputs, OrderedDict):
                return OrderedDict(gen_expr)
            return dict(gen_expr)
        return inputs

    @staticmethod
    def json_comments(text):
        comment_re = re.compile(r'((?:^|[A-Za-zА-Яа-я\d.{}\[\]]+|(?=((?<=").*"))\2),?)\s*/{2}.*$')
        lines = text.split('\n')
        excluded = {}
        for lineNum, line in enumerate(lines):
            match = comment_re.search(line)
            if not match:
                continue
            split_at = match.end(1)
            lines[lineNum] = new_line = line[:split_at]
            excluded[lineNum] = (line[split_at:], not bool(new_line))
        return '\n'.join([lines[i] for i in xrange(len(lines)) if i not in excluded or not excluded[i][1]]), excluded

    @staticmethod
    def encrypt(line):
        return line.encode('zlib').encode('base64')

    @staticmethod
    def decrypt(line, encrypted):
        if not line:
            return line, encrypted
        try:
            return line.decode('base64').decode('zlib'), True
        except (UnicodeEncodeError, binascii.Error, zlib.error):
            return line, False

    @staticmethod
    def json_dumps(conf, sort):  # noinspection PyArgumentEqualDefault
        return json.dumps(
            conf, sort_keys=sort, indent=4, ensure_ascii=False, encoding='utf-8', separators=(',', ': '), cls=JSONEncoder)

    @classmethod
    def json_file_read(cls, new_path, encrypted):
        read_contents = ''
        read_excluded = {}
        success = True
        try:
            kwargs = {'mode': 'r', 'encoding': 'utf-8-sig'} if not encrypted else {'mode': 'rb'}
            with codecs.open(new_path, **kwargs) as json_file:
                read_contents, isEncrypted = cls.decrypt(json_file.read(), encrypted)
                if not isEncrypted and encrypted:
                    read_contents = read_contents.decode('utf-8-sig')
                read_contents, read_excluded = cls.json_comments(read_contents)
        except StandardError:
            print new_path
            traceback.print_exc()
            if not encrypted:
                print read_contents.replace('\r', '')
            success = False
        return read_contents, read_excluded, success

    @classmethod
    def json_file_write(cls, new_path, data, encrypted):
        kwargs = {'mode': 'w', 'encoding': 'utf-8-sig'} if not encrypted else {'mode': 'wb'}
        with codecs.open(new_path, **kwargs) as json_file:
            if encrypted:
                data = cls.encrypt(data)
            json_file.write(data)

    @classmethod
    def loadJson(cls, ID, name, oldConfig, path, save=False, rewrite=True, quiet=False, encrypted=False, sort_keys=True):
        config_new = oldConfig
        oldConfig = cls.stringed_ints(oldConfig)
        if not os.path.exists(path):
            os.makedirs(path)
        if not path.endswith('/'):
            path += '/'
        new_path = '%s%s.json' % (path, name)
        if not os.path.isfile(new_path):
            if not save:
                print ID + ': ERROR: Config not found, creating default:', new_path
            cls.json_file_write(new_path, cls.json_dumps(oldConfig, sort_keys), encrypted)
            return config_new
        if not save:
            data, _, success = cls.json_file_read(new_path, encrypted)
            if not success:
                return config_new
            try:
                config_new = cls.byte_ify(json.loads(data, object_hook=cls.byte_ify), ignore_dicts=True)
            except StandardError:
                print new_path
                traceback.print_exc()
            return config_new
        read_contents, read_excluded, success = cls.json_file_read(new_path, encrypted)
        if not success:
            read_contents = cls.json_dumps(oldConfig, sort_keys)
        read_data = cls.byte_ify(json.loads(read_contents, object_pairs_hook=OrderedDict))  # maintains ordering
        if rewrite:
            updated = read_data != oldConfig
            read_data = oldConfig
            sort_keys = not isinstance(oldConfig, OrderedDict)
        else:
            updated = smart_update(read_data, oldConfig)
            sort_keys = False
        if not updated:
            return config_new
        write_lines = cls.byte_ify(cls.json_dumps(read_data, sort_keys)).split('\n')
        if not quiet:
            print ID + ': updating config:', new_path
        for lineNum, (comment, insert) in sorted(read_excluded.iteritems(), key=lambda x: x[0]):
            if not insert:
                if lineNum < len(write_lines):
                    write_lines[lineNum] += comment
                    continue
                else:
                    print ID + ': config', new_path, 'update warning: comment on line', lineNum, 'went beyond updated file'
            write_lines.insert(lineNum, comment)
        cls.json_file_write(new_path, '\n'.join(write_lines), encrypted)
        return config_new

    @classmethod
    def loadJsonOrdered(cls, ID, path, name):
        config_new = None
        if not os.path.exists(path):
            os.makedirs(path)
        if not path.endswith('/'):
            path += '/'
        new_path = '%s%s.json' % (path, name)
        if not os.path.isfile(new_path):
            print ID + ': ERROR: Config not found:', new_path
            return config_new
        data, _, success = cls.json_file_read(new_path, False)
        if not success:
            return config_new
        try:
            config_new = cls.byte_ify(json.loads(data, object_pairs_hook=OrderedDict))
        except StandardError:
            print new_path
            traceback.print_exc()
        return config_new


loadJson = JSONLoader.loadJson
loadJsonOrdered = JSONLoader.loadJsonOrdered
