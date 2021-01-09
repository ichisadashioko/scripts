#!/usr/bin/env python3
# encoding=utf-8
import os
import sys
import subprocess
import argparse
import urllib.request
import traceback

IGNORED_FILES = [
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


def find_all_java_files(infile: str, out_list: list):
    basename = os.path.basename(infile)
    if basename.lower() in IGNORED_FILES:
        return

    if os.path.isfile(infile):
        ext = os.path.splitext(basename)[1].lower()
        if ext == '.java':
            out_list.append(infile)
    elif os.path.isdir(infile):
        flist = os.listdir(infile)
        for fname in flist:
            fpath = os.path.join(infile, fname)
            find_all_java_files(infile=fpath, out_list=out_list)


def find_java_files_tracked_by_git(infile: str):
    git_process = subprocess.run(
        args=['git', 'ls-files'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.abspath(infile),
    )

    if (len(git_process.stderr) > 0) or (git_process.returncode != 0):
        _, error_msg = Encoding.decode(git_process.stderr)

        if type(error_msg) is bytes:
            error_msg = str(error_msg)

        raise Exception(
            'returncode: '
            + repr(git_process.returncode)
            + 'stderr: '
            + error_msg
        )

    encoding, decoded_output = Encoding.decode(git_process.stdout)
    if (encoding is None) or (type(decoded_output) is bytes):
        print(git_process.stdout)
        raise Exception('Failed to decode the git output!')

    output_lines = decoded_output.split('\n')
    rel_fpaths = filter(lambda x: len(x) > 0, output_lines)
    fpaths = map(lambda x: os.path.join(infile, x), rel_fpaths)
    fpaths = filter(lambda x: os.path.exists(x), fpaths)
    fpaths = filter(lambda x: os.path.isfile(x), fpaths)
    fpaths = filter(lambda x: os.path.splitext(x)[1].lower() == '.java', fpaths)
    fpaths = list(fpaths)

    return fpaths


def ensure_lf_line_ending(s: str):
    s = s.replace('\r\n', '\n')
    s = s.replace('\r', '\n')
    return s


def remove_trailing_spaces_or_tabs(s: str):
    lines = s.split('\n')

    ret_lines = []
    for line in lines:
        if len(line) == 0:
            ret_lines.append(line)
        else:
            while True:
                if len(line) == 0:
                    break
                else:
                    last_char = line[-1]
                    if last_char == ' ':
                        line = line.rstrip(' ')
                    elif last_char == '\t':
                        line = line.rstrip('\t')
                    else:
                        break

            ret_lines.append(line)

    ret = '\n'.join(ret_lines)
    return ret


def remove_leading_empty_lines(s: str):
    s = s.lstrip('\n')
    return s


def ensure_extractly_one_empty_line_at_the_end(s: str):
    s = s.rstrip('\n')
    s = s + '\n'
    return s


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'infile',
        default='.',
        action='store',
        nargs='?',
        help=(
            'Specify file for directory to format.'
            ' If a file is specified,'
            ' then the --git and --nogit options are ignored.'
        ),
    )

    parser.add_argument('--git', help='use git to list tracked files')
    parser.add_argument('--nogit', help='force disable git detection', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--verbose', '-v', action='store_true')

    args = parser.parse_args()
    print(args)

    fpath_list = []

    gjf_process_cwd = ''

    if not os.path.exists(args.infile):
        print(args.infile + ' does not exist!', file=sys.stderr)
        sys.exit(-1)
    elif os.path.isfile(args.infile):
        fpath_list.append(args.infile)
        gjf_process_cwd = os.getcwd()
    elif os.path.isdir(args.infile):
        gjf_process_cwd = args.infile
        # list and append file to the pending list
        if args.nogit:
            find_all_java_files(infile=args.infile, out_list=fpath_list)
        if args.git:
            # force to use git to list file
            # fatal error if the directory is not belong to a git repo
            fpath_list = find_java_files_tracked_by_git(args.infile)
        else:
            # detect git
            try:
                tmp_fpath_list = find_java_files_tracked_by_git(args.infile)
                fpath_list = tmp_fpath_list
            except Exception as ex:
                print()
                print(TermColor.FG_BRIGHT_RED)
                print('Failed to use git to list files!')
                traceback.print_exc()
                print(TermColor.RESET_COLOR)

                find_all_java_files(infile=args.infile, out_list=fpath_list)
    else:
        print('This should not be executed!', file=sys.stderr)
        sys.exit(-1)

    # Download google-java-format binary

    TMP_DIR_ENV_VAR_NAME = 'SHIOKO_JAVA_FORMMATTER_TMP_DIR'

    if TMP_DIR_ENV_VAR_NAME in os.environ:
        tmp_dir_value = os.environ[TMP_DIR_ENV_VAR_NAME]
    else:
        tmp_dir_value = os.path.dirname(os.path.abspath(__file__))

    # print('tmp_dir_value: ' + tmp_dir_value)

    gjf_bin_url = 'https://github.com/google/google-java-format/releases/download/google-java-format-1.9/google-java-format-1.9-all-deps.jar'

    gjf_bin_filename = gjf_bin_url.split('/')[-1]

    # print('gjf_bin_filename: ' + gjf_bin_filename)

    gjf_bin_filepath = os.path.join(tmp_dir_value, gjf_bin_filename)

    print('gjf_bin_filepath: ' + gjf_bin_filepath)

    if not os.path.exists(gjf_bin_filepath):
        print('Downloading google-java-format binary...')
        res = urllib.request.urlopen(gjf_bin_url)
        # TODO handle failed request
        if not os.path.exists(tmp_dir_value):
            os.makedirs(tmp_dir_value)

        with open(gjf_bin_filepath, mode='wb') as outfile:
            outfile.write(res.read())

    for fpath in fpath_list:
        print('>', fpath, end=' ')
        filesize = os.path.getsize(fpath)
        if filesize == 0:
            # skip empty file
            if args.verbose:
                print((
                    '- '
                    + TermColor.FG_BRIGHT_YELLOW
                    + 'SKIP_EMPTY'
                    + TermColor.RESET_COLOR
                ),)
            else:
                print('\r', end='')
                continue

        bs = open(fpath, mode='rb').read()
        gjf_process = subprocess.run(
            args=[
                'java',
                '-jar',
                gjf_bin_filepath,
                '--aosp',
                '--skip-reflowing-long-strings',
                fpath,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.abspath(gjf_process_cwd),
        )

        if (len(gjf_process.stderr) > 0) or (gjf_process.returncode != 0):
            print(TermColor.FG_BRIGHT_RED, end='', file=sys.stderr)
            print('\nGoogle Java Format failed or exited with non-zero status code!', file=sys.stderr)
            print('returncode:', gjf_process.returncode, file=sys.stderr)

            _, error_msg = Encoding.decode(gjf_process.stderr)
            if type(error_msg) is bytes:
                print('Cannot decode Google Java Format stderr!', file=sys.stderr)
                error_msg = str(error_msg)

            print('stderr:', error_msg, file=sys.stderr, end='')
            print(TermColor.RESET_COLOR, file=sys.stderr)
            sys.exit(-1)

        _, formatted_java_code = Encoding.decode(gjf_process.stdout)

        if type(formatted_java_code) is bytes:
            print(TermColor.FG_BRIGHT_RED, end='', file=sys.stderr)
            print('Cannot decode Google Java Format stdout!', file=sys.stderr)
            print('stdout:', formatted_java_code, end='', file=sys.stderr)
            print(TermColor.RESET_COLOR, file=sys.stderr)
            sys.exit(-1)

        formatted_java_code = ensure_lf_line_ending(formatted_java_code)
        formatted_java_code = remove_trailing_spaces_or_tabs(formatted_java_code)
        formatted_java_code = remove_leading_empty_lines(formatted_java_code)
        formatted_java_code = ensure_extractly_one_empty_line_at_the_end(formatted_java_code)

        formatted_bs = formatted_java_code.encode('utf-8')

        if bs == formatted_bs:
            if args.verbose:
                print(
                    TermColor.FG_BRIGHT_GREEN
                    + 'OK'
                    + TermColor.RESET_COLOR
                )
            else:
                print(end='\r')
        else:
            if args.run:
                os.remove(fpath)
                with open(fpath, mode='wb') as outfile:
                    outfile.write(formatted_bs)

                print(
                    TermColor.FG_BRIGHT_RED
                    + 'x'
                    + TermColor.RESET_COLOR
                    + ' -> '
                    + TermColor.FG_BRIGHT_GREEN
                    + 'OK'
                    + TermColor.RESET_COLOR
                )
            else:
                print(
                    TermColor.FG_BRIGHT_RED
                    + 'x'
                    + TermColor.RESET_COLOR
                )
