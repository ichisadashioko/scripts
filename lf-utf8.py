#!/usr/bin/env python3
# encoding=utf-8
import os
import sys
import subprocess
import argparse
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


skips = [
    '.git',  # git directory
    'logs',  # log directory
    'backup',  # Visual Studio project migration files
    # known Visual Studio files
    'bin',
    'obj',
    '.vs',
    'debug',
    'release',
]

skip_extensions = [
    '.bomb',
    '.map',
    # Microsoft Excel files
    '.xls',
    # known binary extensions
    '.dll',
    '.jpg',
    '.gif',
    '.png',
    '.jpeg',
    '.jar',
    '.jad',
    # weird files from Visual Studio
    '.suo',
    '.exe',
    '.pdb',
    '.ilk',
    '.i64',
    '.idb',
    # Microsoft Windows files
    '.ini',
]


def find_all_files(infile: str) -> List[str]:
    basename = os.path.basename(infile)
    if basename.lower() in skips:
        return []

    retval = []

    if os.path.isfile(infile):
        ext = os.path.splitext(infile)[1].lower()
        if ext in skip_extensions:
            return []
        else:
            return [infile]

    elif os.path.isdir(infile):
        flist = os.listdir(infile)
        for fname in flist:
            fpath = os.path.join(infile, fname)
            retval.extend(find_all_files(fpath))

    return retval


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

    # If the file appears in git but it is a directory then it is probably a git submodule
    # TODO modules which are not initialized may appear as files
    filepaths = filter(lambda x: os.path.isfile(x), filepaths)

    filepaths = filter(lambda x: not os.path.splitext(x)[1].lower() in skip_extensions, filepaths)

    filepaths = list(filepaths)

    return filepaths


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('infile', default='.', action='store', nargs='?')
    parser.add_argument('--git', help='use git to list file', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--verbose', action='store_true')

    args = parser.parse_args()
    print(args)

    file_list = os.listdir(args.infile)

    for file_name in file_list:
        if file_name == '.git':
            args.git = True
            break

    if args.git:
        filepaths = list_git_files(args.infile)
    else:
        filepaths = find_all_files(args.infile)

    for filepath in filepaths:
        print('>', filepath, end=' ')

        basename = os.path.basename(filepath)
        ext = os.path.splitext(basename)[1]

        # git will not filter these extensions
        if ext.lower() in skip_extensions:
            print('\r', end='')
            continue

        bs = open(filepath, mode='rb').read()
        if len(bs) == 0:
            # empty file
            if args.verbose:
                print(f'{TermColor.FG_BRIGHT_GREEN}OK{TermColor.RESET_COLOR}')
            else:
                print('\r', end='')

        encoding, decoded_string = Encoding.decode(bs)

        if (encoding is None) or (type(decoded_string) is bytes):
            print('\r', end='')
            continue

        # enforce LF line ending
        content = decoded_string.replace('\r\n', '\n')
        content = content.strip('\n')

        # append empty line at the end
        # it's good practice for Git
        content = content + '\n'
        encoded_content = content.encode(Encoding.UTF8)

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
