#!/usr/bin/env python
from setuptools import setup, find_packages, Command
from setuptools.command.build_py import build_py

import os
import re
import tokenize as std_tokenize
from tokenize import ASYNC, AWAIT, NAME, NEWLINE, NL, STRING, ENCODING
import codecs
import shutil
import sys

here = os.path.abspath(os.path.dirname(__file__))
VERSION = '0.0.1'
ASYNC_TO_SYNC = {
    '__aenter__': '__enter__',
    '__aexit__': '__exit__',
    '__aiter__': '__iter__',
    '__anext__': '__next__',
    # TODO StopIteration is still accepted in Python 2, but the right change
    # is 'raise StopAsyncIteration' -> 'return' since we want to use bleached
    # code in Python 3.7+
    'StopAsyncIteration': 'StopIteration',
}


class CompileCommand(Command):
    """Support setup.py upload."""
    description = 'Build the package.'
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status('Removing previous builds…')
            shutil.rmtree(os.path.join(here, 'build'))
        except OSError:
            pass
        self.status('Compiling sync code…')
        os.system(f'{sys.executable} {__file__} build')
        self.status('Moving things around…')
        os.system('rm -fr requests_core/_http/_sync')
        os.system(
            'mv build/lib/requests_core/_http/_sync/ requests_core/_http/'
        )
        try:
            self.status('Cleaning up…')
            shutil.rmtree(os.path.join(here, 'build'))
        except OSError:
            pass
        sys.exit()


def tokenize(f):
    last_end = (1, 0)
    for tok in std_tokenize.tokenize(f.readline):
        if tok.type == ENCODING:
            continue

        if last_end[0] < tok.start[0]:
            yield ('', STRING, ' \\\n')

            last_end = (tok.start[0], 0)
        space = ''
        if tok.start > last_end:
            assert tok.start[0] == last_end[0]
            space = ' ' * (tok.start[1] - last_end[1])
        yield (space, tok.type, tok.string)

        last_end = tok.end
        if tok.type in [NEWLINE, NL]:
            last_end = (tok.end[0] + 1, 0)


def bleach_tokens(tokens):
    # TODO __await__, ...?
    used_space = None
    for space, toknum, tokval in tokens:
        if toknum in [ASYNC, AWAIT]:  # TODO Python 3.7+
            # When remove async or await, we want to use the whitespace that
            # was before async/await before the next token so that
            # `print(await stuff)` becomes `print(stuff)` and not
            # `print( stuff)`
            used_space = space
        else:
            if toknum == NAME and tokval in ASYNC_TO_SYNC:
                tokval = ASYNC_TO_SYNC[tokval]
            if used_space is None:
                used_space = space
            yield (used_space, tokval)

            used_space = None


def untokenize(tokens):
    return ''.join(space + tokval for space, tokval in tokens)


def bleach(filepath, fromdir, todir):
    with open(filepath, 'rb') as f:
        encoding, _ = std_tokenize.detect_encoding(f.readline)
        f.seek(0)
        tokens = tokenize(f)
        tokens = bleach_tokens(tokens)
        result = untokenize(tokens)
        outfilepath = filepath.replace(fromdir, todir)
        os.makedirs(os.path.dirname(outfilepath), exist_ok=True)
        with open(outfilepath, 'w', encoding=encoding) as f:
            print(result, file=f, end='')


class bleach_build_py(build_py):
    """Monkeypatches build_py to add bleaching from _async to _sync"""

    def run(self):
        self._updated_files = []
        # Base class code
        if self.py_modules:
            self.build_modules()
        if self.packages:
            self.build_packages()
            self.build_package_data()
        for f in self._updated_files:
            if '/_async/' in f:
                bleach(f, '_async', '_sync')
        # Remaining base class code
        self.byte_compile(self.get_outputs(include_bytecode=0))

    def build_module(self, module, module_file, package):
        outfile, copied = super().build_module(module, module_file, package)
        if copied:
            self._updated_files.append(outfile)
        return outfile, copied


setup(
    name='requests-core',
    version=VERSION,
    description="Experimental lower-level async HTTP client for Requests 3.0",
    # long_description=u'\n\n'.join([readme, changes]),
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries',
    ],
    keywords='urllib httplib threadsafe filepost http https ssl pooling',
    author='Kenneth Reitz',
    author_email='me@kennethreitz.org',
    url='https://github.com/kennethreitz/requests-core',
    license='MIT',
    packages=find_packages(),
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, <4",
    tests_require=['pytest', 'mock', 'tornado'],
    # These are a less-specific subset of dev-requirements.txt, for the
    # convenience of distro package maintainers.
    test_suite='test',
    install_requires=["h11"],
    extras_require={
        'secure': [
            'pyOpenSSL>=0.14',
            'cryptography>=1.3.4',
            'idna>=2.0.0',
            'certifi',
            "ipaddress",
        ],
        'socks': ['PySocks>=1.5.6,<2.0,!=1.5.7'],
    },
    cmdclass={'build_py': bleach_build_py, 'compile': CompileCommand},
)
