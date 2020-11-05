#!/usr/bin/env python3
# encoding=utf-8
import os
import sys
import subprocess
import argparse
import json
from typing import List


class TermColor:
    RESET_COLOR = '\033[0m'
    FG_RED = '\033[31m'
    FG_GREEN = '\033[32m'
    FG_YELLOW = '\033[33m'
    FG_BLUE = '\033[34m'
    FG_BRIGHT_RED = '\033[91m'
    FG_BRIGHT_GREEN = '\033[92m'
    FG_BRIGHT_YELLOW = '\033[93m'
    FG_BRIGHT_BLUE = '\033[94m'
    FG_BRIGHT_MAGENTA = '\033[95m'


class Encoding:
    UTF8 = 'utf-8'
    UTF8_WITH_BOM = 'utf-8-sig'
    UTF16 = 'utf-16'
    GB2312 = 'gb2312'
    SHIFT_JIS = 'shift-jis'

    @classmethod
    def decode(cls, bs: bytes):
        try:
            encoding = cls.UTF8_WITH_BOM
            decoded_content = bs.decode(encoding)
            return encoding, decoded_content
        except Exception as ex:
            # traceback.print_exc()
            pass

        try:
            encoding = cls.UTF8
            decoded_content = bs.decode(encoding)
            return encoding, decoded_content
        except Exception as ex:
            # traceback.print_exc()
            pass

        try:
            encoding = cls.UTF16
            decoded_content = bs.decode(encoding)
            return encoding, decoded_content
        except Exception as ex:
            # traceback.print_exc()
            pass

        try:
            encoding = cls.GB2312
            decoded_content = bs.decode(encoding)
            return encoding, decoded_content
        except Exception as ex:
            # traceback.print_exc()
            pass

        try:
            encoding = cls.SHIFT_JIS
            decoded_content = bs.decode(encoding)
            return encoding, decoded_content
        except Exception as ex:
            # traceback.print_exc()
            pass

        return None, bs


IGNORED_DIRS = [
    '.git',  # git directory
    'logs',  # log directory
    'backup',  # Visual Studio project migration files
    # known Visual Studio files
    'bin',
    'obj',
    '.vs',
    'debug',
    'release',
    '.ipynb_checkpoints',
    '__pycache__',
]


def find_all_ipynb_files(infile: str, out_list: list):
    basename = os.path.basename(infile)
    if basename.lower() in IGNORED_DIRS:
        return []

    retval = []

    if os.path.isdir(infile):
        flist = os.listdir(infile)
        for fname in flist:
            fpath = os.path.join(infile, fname)
            retval.extend(find_all_ipynb_files(infile=fpath))

    elif os.path.isfile(infile):
        ext = os.path.splitext(infile)[1].lower()
        if ext == '.ipynb':
            out_list.append(infile)


def list_git_files(indir: str):
    git_process = subprocess.run(
        args=['git', 'ls-files'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=indir,
    )

    if len(git_process.stderr) > 0:
        _, error_msg = Encoding.decode(git_process.stderr)

        if type(error_msg) is bytes:
            error_msg = str(error_msg)

        raise Exception(error_msg)

    encoding, decoded_output = Encoding.decode(git_process.stdout)
    if (encoding is None) or (type(decoded_output) is bytes):
        print(git_process.stdout)
        raise Exception('Failed to decode the git output!')

    output_lines = decoded_output.split('\n')
    rel_filepaths = filter(lambda x: len(x) > 0, output_lines)
    filepaths = map(lambda x: os.path.join(indir, x), rel_filepaths)
    filepaths = filter(lambda x: os.path.exists(x), filepaths)
    filepaths = filter(lambda x: os.path.isfile(x), filepaths)
    filepaths = list(filepaths)

    return filepaths


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('infile', default='.', action='store', nargs='?')
    parser.add_argument('--git', help='use git to list file', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true')

    args = parser.parse_args()
    print(args)

    file_list = os.listdir(args.infile)

    for file_name in file_list:
        if file_name == '.git':
            args.git = True
            break

    if args.git:
        filepaths = list_git_files(args.infile)
        filepaths = filter(lambda filepath: os.path.splitext(filepath)[1].lower() == '.ipynb', filepaths)
        filepaths = list(filepaths)
    else:
        filepaths = find_all_ipynb_files(args.infile)

    for filepath in filepaths:
        print('>', filepath, end=' ')

        filesize = os.path.getsize(filepath)
        if filesize == 0:
            print('\r', end='')
            continue

        bs = open(filepath, mode='rb').read()

        encoding, decoded_string = Encoding.decode(bs)

        if (encoding is None) or (type(decoded_string) is bytes):
            print('\r', end='')
            continue

        obj = json.loads(decoded_string)
        if 'version' in obj['metadata']['language_info']:
            del obj['metadata']['language_info']['version']

        json_str = json.dumps(
            obj=obj,
            ensure_ascii=False,
            indent='\t',
        )

        if not json_str[-1] == '\n':
            json_str += '\n'

        encoded_content = json_str.encode(Encoding.UTF8)

        if encoded_content == bs:
            if args.verbose:
                print(f'{TermColor.FG_BRIGHT_GREEN}OK{TermColor.RESET_COLOR}')
            else:
                print('\r', end='')
        else:
            if args.run:
                os.remove(filepath)  # file content may not be changed if we don't remove it
                with open(filepath, mode='wb') as outfile:
                    outfile.write(encoded_content)

                print(f'{TermColor.FG_RED}x{TermColor.RESET_COLOR} -> {TermColor.FG_BRIGHT_GREEN}OK{TermColor.RESET_COLOR}')
            else:
                print(f'{TermColor.FG_RED}x{TermColor.RESET_COLOR}')


if __name__ == '__main__':
    main()
