#!/usr/bin/env python3
# encoding=utf-8
import os
import subprocess
import argparse
import stat
import typing

RESET = '\033[0m'
RED = '\033[91m'
GREEN = '\033[92m'
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

IGNORED_EXTS = [
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
    '.iso',
    '.mds',
    '.dat',
    # weird files from Visual Studio
    '.suo',
    '.exe',
    '.pdb',
    '.ilk',
    '.i64',
    '.idb',
    # Microsoft Windows files
    '.ini',
    # opencore binaries
    '.aml',
    '.bin',
    '.ico',
]


def find_regular_files(inpath: str) -> typing.List[str]:
    basename = os.path.basename(inpath)
    if basename.lower() in IGNORED_DIRS:
        return []

    regular_filepath_list = []

    file_stat = os.stat(inpath)

    if stat.S_ISDIR(file_stat.st_mode):
        child_filename_list = os.listdir(inpath)
        for child_filename in child_filename_list:
            child_filepath = os.path.join(inpath, child_filename)
            regular_filepath_list.extend(find_regular_files(child_filepath))
    elif stat.S_ISREG(file_stat.st_mode):
        ext = os.path.splitext(inpath)[1].lower()
        if ext not in IGNORED_EXTS:
            regular_filepath_list.append(inpath)

    return regular_filepath_list


def find_regular_files_from_git(inpath: str):
    git_process = subprocess.run(
        args=['git', 'ls-files'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=inpath,
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

    filepath_list = []

    for line in output_lines:
        line = line.strip()
        if len(line) == 0:
            continue

        basename = os.path.basename(line)
        if basename.lower() in IGNORED_DIRS:
            continue

        filepath = os.path.join(inpath, line)
        if not os.path.exists(filepath):
            continue

        file_stat = os.stat(filepath)
        # If the file appears in git but it is a directory then it is probably a git submodule
        if stat.S_ISREG(file_stat.st_mode):
            ext = os.path.splitext(filepath)[1].lower()
            if ext not in IGNORED_EXTS:
                filepath_list.append(filepath)

    return filepath_list


def format_text_file_content(content: str):
    # enforce LF line ending
    content = content.replace('\r', '')

    # strip all leading and trailing new line characters
    content = content.strip('\n')

    # remove trailing whitespace or tab characters
    content_lines = content.split('\n')

    formatted_lines = []
    for line in content_lines:
        line = line.rstrip()
        line = line.rstrip('\t')
        formatted_lines.append(line)

    content = '\n'.join(formatted_lines)

    # append empty line at the end
    # it's good practice for Git
    content = content + '\n'

    return content


def format_text_file(inpath: str):
    content_bs = open(inpath, mode='rb').read()

    encoding, decoded_string = Encoding.decode(content_bs)

    if (encoding is None) or (type(decoded_string) is bytes):
        return {
            'error': 'Failed to decode the file!',
        }

    content = format_text_file_content(decoded_string)
    encoded_content = content.encode(Encoding.UTF8)

    if content_bs == encoded_content:
        return {
            'diff': False,
        }
    else:
        return {
            'diff': True,
            'content_bs': encoded_content,
        }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('infile', default='.', action='store', nargs='?')
    parser.add_argument('-git', '--git', help='use git to list file', action='store_true')
    parser.add_argument('-noautogit', '--noautogit', action='store_true')
    parser.add_argument('-r', '--r', '-run', '--run', dest='run', action='store_true')
    parser.add_argument('-v', '--v', '-verbose', '--verbose', dest='verbose', action='store_true')

    args = parser.parse_args()
    print(args)

    inpath = args.infile
    use_git = args.git
    no_auto_git = args.noautogit
    is_run = args.run
    verbose = args.verbose

    filepath_list = []

    if not os.path.exists(inpath):
        raise Exception(inpath + ' does not exist!')
    elif os.path.isfile(inpath):
        filepath_list.append(inpath)
    elif os.path.isdir(inpath):
        if not no_auto_git:
            child_filename_list = os.listdir(inpath)
            use_git = ('.git' in child_filename_list)

        if use_git:
            filepath_list = find_regular_files_from_git(inpath)
        else:
            filepath_list = find_regular_files(inpath)

    MAX_FILESIZE = 1024 * 1024 * 10  # 10 MBs
    for filepath in filepath_list:
        print('>', filepath, end=' ')

        basename = os.path.basename(filepath)
        ext = os.path.splitext(basename)[1]

        # git will not filter these extensions
        if ext.lower() in IGNORED_EXTS:
            print('\r', end='')
            continue

        filesize = os.path.getsize(filepath)
        if (filesize == 0) or (filesize > MAX_FILESIZE):
            print(f'- {RED}file is too big ({filesize}){RESET}', flush=True)
            continue

        format_result = format_text_file(filepath)

        if 'error' in format_result:
            error_msg = format_result['error']
            print(f'- {RED}{error_msg}{RESET}', flush=True)
            continue

        if format_result['diff']:
            if is_run:
                content_bs = format_result['content_bs']
                os.remove(filepath)  # file content may not be changed if we don't remove it
                with open(filepath, mode='wb') as outfile:
                    outfile.write(content_bs)

                print(f'{RED}x{RESET} -> {GREEN}OK{RESET}', flush=True)
            else:
                print(f'{RED}x{RESET}', flush=True)
        else:
            if verbose:
                print(f'{GREEN}OK{RESET}', flush=True)
            else:
                print('\r', end='')


if __name__ == '__main__':
    main()
