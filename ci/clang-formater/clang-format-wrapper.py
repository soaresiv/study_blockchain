#!/usr/bin/env python3
"""A wrapper script around clang-format, suitable for linting multiple files
and to use for continuous integration.

This is an alternative API for the clang-format command line.
It runs over multiple files and directories in parallel.
A diff output is produced and a sensible exit code is returned.

"""

import argparse
import difflib
import fnmatch
from functools import partial
import io
import multiprocessing
import os
import signal
import subprocess
import sys
import traceback
from subprocess import DEVNULL


DEFAULT_EXTENSIONS = 'c,h,C,H,cpp,hpp,cc,hh,c++,h++,cxx,hxx'
DEFAULT_CLANG_FORMAT_IGNORE = '.clang-format-ignore'
DEFAULT_CLANG_FORMAT_PATH = '/usr/bin/clang-format-13'
DEFAULT_CLANG_FORMAT_STYLE = 'Google'
DEFAULT_WORKPLACE_PATH = '.'


class ExitStatus:
    SUCCESS = 0
    DIFF = 1
    TROUBLE = 2


def excludes_from_file(ignore_file):
    excludes = []
    if os.path.exists(ignore_file):
        with io.open(ignore_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('#'):
                    # ignore comments
                    continue
                pattern = line.rstrip()
                if not pattern:
                    # allow empty lines
                    continue
                excludes.append(pattern)

    return excludes


def isEmpty(string):
    return not (string and string.strip())


def list_files(path, extensions=DEFAULT_EXTENSIONS, exclude=None):
    if extensions is None:
        extensions = []
    if exclude is None:
        exclude = []

    files_filtered = []
    files_to_be_remove = []

    if os.path.isdir(path):
        for dirpath, dnames, fnames in os.walk(path):
            fpaths = [os.path.relpath(os.path.join(
                dirpath, fname), path) for fname in fnames]
            for file in fpaths:
                ext = os.path.splitext(file)[1][1:]
                if not isEmpty(ext):
                    if ext in extensions:
                        files_filtered.append(file)
    else:
        print_trouble('list_files', f'No such folder: {path}', False)
        return files_filtered

    for file in files_filtered:
        for pattern in exclude:
            if fnmatch.fnmatch(file, pattern):
                files_to_be_remove.append(file)

    files_filtered[:] = [
        d for d in files_filtered if d not in files_to_be_remove]

    files_filtered = [os.path.join(path, x) for x in files_filtered]

    return files_filtered


def make_diff(file, original, reformatted):
    return list(
        difflib.unified_diff(
            original,
            reformatted,
            fromfile='{}\t(original)'.format(file),
            tofile='{}\t(reformatted)'.format(file),
            n=3))


class DiffError(Exception):
    def __init__(self, message, errs=None):
        super(DiffError, self).__init__(message)
        self.errs = errs or []


class UnexpectedError(Exception):
    def __init__(self, message, exc=None):
        super(UnexpectedError, self).__init__(message)
        self.formatted_traceback = traceback.format_exc()
        self.exc = exc


def run_clang_format_diff_wrapper(args, file):
    try:
        ret = run_clang_format_diff(args, file)
        return ret
    except DiffError:
        raise
    except Exception as e:
        raise UnexpectedError('{}: {}: {}'.format(file, e.__class__.__name__,
                                                  e), e)


def run_clang_format_diff(args, file):
    try:
        with io.open(file, 'r', encoding='utf-8') as f:
            original = f.readlines()
    except IOError as exc:
        raise DiffError(str(exc))

    if args.in_place:
        invocation = [args.clang_format_executable, '-i', file]
    else:
        invocation = [args.clang_format_executable, file]

    if args.fallback:
        invocation.extend(['--fallback-style', args.fallback])

    if args.dry_run:
        print(" ".join(invocation))
        return [], []

    try:
        proc = subprocess.run(
            args=invocation,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=args.workplace,
            universal_newlines=True,
            encoding='utf-8',
        )
    except OSError as exc:
        raise DiffError(
            "Command '{}' failed to start: {}".format(
                subprocess.list2cmdline(invocation), exc
            )
        )
    proc_stdout = proc.stdout
    proc_stderr = proc.stderr

    # hopefully the stderr pipe won't get full and block the process
    outs = list(proc_stdout.splitlines(True))
    errs = list(proc_stderr.splitlines(True))
    if proc.returncode:
        raise DiffError(
            "Command '{}' returned non-zero exit status {}".format(
                subprocess.list2cmdline(invocation), proc.returncode
            ),
            errs,
        )
    if args.in_place:
        return [], errs
    return make_diff(file, original, outs), errs


def bold_red(s):
    return '\x1b[1m\x1b[31m' + s + '\x1b[0m'


def colorize(diff_lines):
    def bold(s):
        return '\x1b[1m' + s + '\x1b[0m'

    def cyan(s):
        return '\x1b[36m' + s + '\x1b[0m'

    def green(s):
        return '\x1b[32m' + s + '\x1b[0m'

    def red(s):
        return '\x1b[31m' + s + '\x1b[0m'

    for line in diff_lines:
        if line[:4] in ['--- ', '+++ ']:
            yield bold(line)
        elif line.startswith('@@ '):
            yield cyan(line)
        elif line.startswith('+'):
            yield green(line)
        elif line.startswith('-'):
            yield red(line)
        else:
            yield line


def print_diff(diff_lines, use_color):
    if use_color:
        diff_lines = colorize(diff_lines)

    sys.stdout.writelines(diff_lines)


def print_trouble(prog, message, use_colors):
    error_text = 'error:'
    if use_colors:
        error_text = bold_red(error_text)
    print("{}: {} {}".format(prog, error_text, message), file=sys.stderr)


def check_clang_version(clang_format_executable):
    version_invocation = [clang_format_executable, str("--version")]
    try:
        subprocess.check_call(version_invocation, stdout=DEVNULL)
    except subprocess.CalledProcessError as e:
        print_trouble('check_clang_version', str(e), use_colors=False)
        return ExitStatus.TROUBLE
    except OSError as e:
        print_trouble(
            'check_clang_version',
            "Command '{}' failed to start: {}".format(
                subprocess.list2cmdline(version_invocation), e
            ),
            use_colors=False,
        )
        return ExitStatus.TROUBLE
    return ExitStatus.SUCCESS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--clang-format-executable',
        metavar='EXECUTABLE',
        help='path to the clang-format executable',
        default=DEFAULT_CLANG_FORMAT_PATH)
    parser.add_argument(
        '-w',
        '--workplace',
        metavar='file',
        help='path to the source root',
        default=DEFAULT_WORKPLACE_PATH)
    parser.add_argument(
        '-d',
        '--dry-run',
        action='store_true',
        help='just print the list of files')
    parser.add_argument(
        '-i',
        '--in-place',
        action='store_true',
        help='format file instead of printing differences')
    parser.add_argument(
        '-q',
        '--quiet',
        action='store_true',
        help="disable output, useful for the exit code")
    parser.add_argument(
        '-j',
        metavar='N',
        type=int,
        default=0,
        help='run N clang-format jobs in parallel'
        ' (default number of cpus + 1)')
    parser.add_argument(
        '--color',
        default='auto',
        choices=['auto', 'always', 'never'],
        help='show colored diff (default: auto)')
    parser.add_argument(
        '-e',
        '--exclude',
        metavar='PATTERN',
        action='append',
        default=[],
        help='exclude paths matching the given glob-like pattern(s)'
        ' from recursive search')
    parser.add_argument(
        '--fallback',
        help='The name of the predefined style used as a fallback in case not find the .clang-format (LLVM, Google, Chromium, Mozilla, WebKit)',
        default=DEFAULT_CLANG_FORMAT_STYLE)
    args = parser.parse_args()

    # use default signal handling, like diff return SIGINT value on ^C
    # https://bugs.python.org/issue14229#msg156446
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    try:
        signal.SIGPIPE
    except AttributeError:
        # compatibility, SIGPIPE does not exist on Windows
        pass
    else:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    colored_stdout = False
    colored_stderr = False
    if args.color == 'always':
        colored_stdout = True
        colored_stderr = True
    elif args.color == 'auto':
        colored_stdout = sys.stdout.isatty()
        colored_stderr = sys.stderr.isatty()

    retcode = check_clang_version(args.clang_format_executable)

    if retcode != ExitStatus.SUCCESS:
        return retcode

    excludes = excludes_from_file(os.path.join(
        args.workplace, DEFAULT_CLANG_FORMAT_IGNORE))
    excludes.extend(args.exclude)

    files = list_files(
        args.workplace,
        exclude=excludes,
    )

    if not files:
        return

    njobs = args.j
    if njobs == 0:
        njobs = multiprocessing.cpu_count() + 1
    njobs = min(len(files), njobs)

    njobs = args.j
    if njobs == 0:
        njobs = multiprocessing.cpu_count() + 1
    njobs = min(len(files), njobs)

    if njobs == 1:
        # execute directly instead of in a pool,
        # less overhead, simpler stacktraces
        it = (run_clang_format_diff_wrapper(args, file) for file in files)
        pool = None
    else:
        pool = multiprocessing.Pool(njobs)
        it = pool.imap_unordered(
            partial(run_clang_format_diff_wrapper, args), files)
        pool.close()
    while True:
        try:
            outs, errs = next(it)
        except StopIteration:
            break
        except DiffError as e:
            print_trouble(parser.prog, str(e), use_colors=colored_stderr)
            retcode = ExitStatus.TROUBLE
            sys.stderr.writelines(e.errs)
        except UnexpectedError as e:
            print_trouble(parser.prog, str(e), use_colors=colored_stderr)
            sys.stderr.write(e.formatted_traceback)
            retcode = ExitStatus.TROUBLE
            # stop at the first unexpected error,
            # something could be very wrong,
            # don't process all files unnecessarily
            if pool:
                pool.terminate()
            break
        else:
            sys.stderr.writelines(errs)
            if outs == []:
                continue
            # if not args.quiet:
            print_diff(outs, use_color=colored_stdout)
            if retcode == ExitStatus.SUCCESS:
                retcode = ExitStatus.DIFF
    if pool:
        pool.join()
    return retcode


if __name__ == '__main__':
    sys.exit(main())
