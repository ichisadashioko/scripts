import os
import stat
import argparse

IGNORED_FILE_NAMES = [
    '.git',
    '.vs',
    '.vscode',
]


def find_visual_studio_config_files(
    inpath: str,
    solution_file_list: list,
    vcxproj_file_list: list,
):
    _, filename = os.path.split(inpath)
    lowered_filename = filename.lower()

    if lowered_filename in IGNORED_FILE_NAMES:
        return

    file_stat = os.stat(inpath)

    if stat.S_ISREG(file_stat.st_mode):
        _, ext = os.path.splitext(lowered_filename)
        if ext == '.sln':
            solution_file_list.append(inpath)
        elif ext == '.vcxproj':
            vcxproj_file_list.append(inpath)
    elif stat.S_ISDIR(file_stat.st_mode):
        child_filename_list = os.listdir(inpath)
        for child_filename in child_filename_list:
            child_filepath = os.path.join(inpath, child_filename)
            find_visual_studio_config_files(
                child_filepath,
                solution_file_list,
                vcxproj_file_list,
            )


SOLUTION_FILE_BLACKLIST_CONFIG = [
    'Debug|x86',
    'Release|x86',
    'Release|x64',
]


def remove_visual_studio_config_from_solution_file(inpath: str):
    content_bs = open(inpath, 'rb').read()
    content_str = content_bs.decode('utf-8')
    lines = content_str.splitlines()

    output_lines = []
    for line in lines:
        detected = False
        for s in SOLUTION_FILE_BLACKLIST_CONFIG:
            if s in line:
                detected = True
                break

        if detected:
            continue

        output_lines.append(line)

    output_str = '\n'.join(output_lines)
    output_str += '\n'
    output_bs = output_str.encode('utf-8')
    is_diff = (content_bs != output_bs)
    return is_diff, output_bs


VXCPROJ_FILE_BLACKLIST_STRING_LIST = [
    'Debug|Win32',
    'Release|Win32',
    'Release|x64',
]

VCXPROJ_FILE_BLACKLIST_CONFIG_INFO_LIST = [
    # (tag_name, attribute_name, attribute_value_list)
    ('ProjectConfiguration', 'Include', VXCPROJ_FILE_BLACKLIST_STRING_LIST),
    ('ImportGroup', 'Condition', VXCPROJ_FILE_BLACKLIST_STRING_LIST),
    ('ItemDefinitionGroup', 'Condition', VXCPROJ_FILE_BLACKLIST_STRING_LIST),
    ('PropertyGroup', 'Condition', VXCPROJ_FILE_BLACKLIST_STRING_LIST),
]


def remove_visual_studio_config_from_vcxproj_file(inpath: str):
    content_bs = open(inpath, 'rb').read()
    content_str = content_bs.decode('utf-8')
    lines = content_str.splitlines()

    output_lines = []

    ignoring_tag_name = None
    for line in lines:
        if ignoring_tag_name is not None:
            if f'</{ignoring_tag_name}>' in line:
                ignoring_tag_name = None
            continue
        else:
            detected = False
            for tag_name, attribute_name, attribute_value_list in VCXPROJ_FILE_BLACKLIST_CONFIG_INFO_LIST:
                if (tag_name in line) and (attribute_name in line):
                    for attribute_value in attribute_value_list:
                        if attribute_value in line:
                            ignoring_tag_name = tag_name
                            detected = True
                            break
                    if detected:
                        break
            if detected:
                continue
            else:
                output_lines.append(line)

    output_str = '\n'.join(output_lines)
    output_str += '\n'
    output_bs = output_str.encode('utf-8')
    is_diff = (content_bs != output_bs)
    return is_diff, output_bs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('inpath', nargs='?', default='.')
    parser.add_argument('-r', '--r', '-run', '--run', dest='run', action='store_true')

    args = parser.parse_args()
    print('args', args)

    inpath = args.inpath
    run = args.run

    solution_file_list = []
    vcxproj_file_list = []

    find_visual_studio_config_files(
        inpath,
        solution_file_list,
        vcxproj_file_list,
    )

    for solution_file in solution_file_list:
        is_diff, output_bs = remove_visual_studio_config_from_solution_file(solution_file)
        if is_diff:
            print(f'x {solution_file}')
            if run:
                open(solution_file, 'wb').write(output_bs)

    for vcxproj_file in vcxproj_file_list:
        is_diff, output_bs = remove_visual_studio_config_from_vcxproj_file(vcxproj_file)
        if is_diff:
            print(f'x {vcxproj_file}')
            if run:
                open(vcxproj_file, 'wb').write(output_bs)


if __name__ == '__main__':
    main()
