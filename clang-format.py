#!/usr/bin/env python3
# encoding=utf-8
import os
import subprocess
import threading
import argparse
import stat
import typing
import traceback

RESET = '\033[0m'
RED = '\033[91m'
GREEN = '\033[92m'


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


SUPPORTED_EXTENSIONS = [
    '.h',
    '.c',
    '.cc',
    '.cpp',
    '.c++',
    '.java',
]


def convert_string(bytes_input: bytes):
    _, s = Encoding.decode(bytes_input)

    if type(s) is bytes:
        # TODO raise error
        return str(bytes_input)
    else:
        return s


class Command:
    def __init__(self, cmd: typing.List[str]):
        self.cmd = cmd

        # type is hinted implicitly (subprocess.Popen)
        self.p = None

        # The process is terminated by us because it took too long.
        # If this flag is True then the output is broken.
        self.terminated = False
        self.stdout = None
        self.stderr = None

    def target(self):
        # print('>', ' '.join(self.cmd))
        self.process = subprocess.Popen(
            self.cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.stdout, self.stderr = self.process.communicate()

    def run(self, timeout=5, raise_on_error=True):
        thread = threading.Thread(target=self.target)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            self.terminated = True
            self.process.terminate()
            # TODO Will call block our main thread for a long time?
            thread.join()

        if raise_on_error:
            if self.terminated:
                raise Exception(f'The process is terminated because it took too long to excute!\n{self.process.__dict__}')

            if (self.process.returncode is None) or (self.process.returncode != 0):
                raise Exception(f'return code is not 0\n{self.process.__dict__}')

            if self.stdout is None:
                raise Exception(f'stdout is None\n{self.process.__dict__}')

            if self.stderr is not None:
                if len(self.stderr) > 0:
                    raise Exception(f'stderr is not empty\n{self.process.__dict__}')


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


def find_clang_supported_files(inpath: str) -> typing.List[str]:
    basename = os.path.basename(inpath)
    if basename.lower() in IGNORED_DIRS:
        return []

    regular_filepath_list = []

    file_stat = os.stat(inpath)

    if stat.S_ISDIR(file_stat.st_mode):
        child_filename_list = os.listdir(inpath)
        for child_filename in child_filename_list:
            child_filepath = os.path.join(inpath, child_filename)
            regular_filepath_list.extend(find_clang_supported_files(child_filepath))
    elif stat.S_ISREG(file_stat.st_mode):
        ext = os.path.splitext(inpath)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            regular_filepath_list.append(inpath)

    return regular_filepath_list


def find_clang_supported_files_from_git(inpath: str):
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
            if ext in SUPPORTED_EXTENSIONS:
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


def format_with_clang_format(inpath: str):
    content_bs = open(inpath, mode='rb').read()

    # TODO check for .clang-format file in the same directory
    # TODO add 'check' or 'format' flags
    cmd = ['clang-format', '-style=file', inpath]
    sp = Command(cmd)

    try:
        sp.run()
    except Exception as ex:
        stacktrace = traceback.format_exc()

        return {
            'error': f'failed to run clang-format\n{ex}\n{stacktrace}',
        }

    clang_formatted_content = convert_string(sp.stdout)
    clang_formatted_content = format_text_file_content(clang_formatted_content)
    encoded_content = clang_formatted_content.encode('utf-8')

    if content_bs == encoded_content:
        return {
            'diff': False,
        }
    else:
        return {
            'diff': True,
            'content_bs': encoded_content,
        }


if __name__ == '__main__':
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
            filepath_list = find_clang_supported_files_from_git(inpath)
        else:
            filepath_list = find_clang_supported_files(inpath)

    for filepath in filepath_list:
        print('>', filepath, end=' ')
        format_result = format_with_clang_format(filepath)

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
