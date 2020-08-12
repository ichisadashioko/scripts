#!/usr/bin/env python3
# encoding=utf-8
import os
import mimetypes
import traceback
import subprocess
import argparse
from typing import List


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
    # weird files from Visual Studio
    '.suo',
    '.exe',
    '.pdb',
    '.ilk',
    '.i64',
    '.idb',
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

    print('stdout:', git_process.stdout)
    print('stderr:', git_process.stderr)

    if len(git_process.stderr) > 0:
        _, error_msg = Encoding.decode(git_process.stderr)

        if type(error_msg) is bytes:
            error_msg = str(error_msg)

        raise Exception(error_msg)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('infile', default='.', action='store', nargs='?')
    parser.add_argument('--git', help='use git to list file', action='store_true')
    parser.add_argument('--run', action='store_true')

    args = parser.parse_args()
    print(args)

    if args.git:
        list_git_files(args.infile)
    else:
        filepaths = find_all_files(args.infile)
        for filepath in filepaths:
            print(filepath)

    return
    # all files
    # filepaths = find_all_files('.')

    # tracked files only
    completed_process = subprocess.run(
        ['git', 'ls-files'],
        stdout=PIPE,
        stderr=PIPE,
    )

    lines = completed_process.stdout.decode('utf-8').split('\n')

    filepaths = filter(lambda x: len(x) > 0, lines)
    filepaths = filter(lambda x: os.path.exists(x), filepaths)
    # probably a git submodule
    # TODO modules which are not initialized may appear as files
    filepaths = filter(lambda x: os.path.isfile(x), filepaths)
    filepaths = list(filepaths)

    for fpath in filepaths:
        print('>', fpath)
        # mime = mimetypes.guess_type(fpath)
        # print(mime, fpath)

        basename = os.path.basename(fpath)
        ext = os.path.splitext(basename)[1].lower()
        if ext in skip_extensions:
            continue

        bs = open(fpath, mode='rb').read()
        encoding, decoded_string = Encoding.decode(bs)

        if (encoding is None) or (type(decoded_string) is bytes):
            continue

        if not encoding == Encoding.UTF8:
            open(fpath, mode='w', encoding=Encoding.UTF8).write(decoded_string)

        # enforce LF line ending
        content = decoded_string.replace('\r\n', '\n')
        content = content.strip('\n')

        # append empty line at the end
        # it's good practice for Git
        content = content + '\n'

        os.remove(fpath)  # file will not be changed if we don't remove it
        with open(fpath, mode='wb') as outfile:
            encoded_content = content.encode(Encoding.UTF8)
            outfile.write(encoded_content)
        # print(encoding, fpath)

if __name__ == '__main__':
    main()
