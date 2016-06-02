#!/usr/bin/env python
# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/unittest-mixins/blob/master/NOTICE.txt

from setuptools import setup

classifiers = """\
Environment :: Console
Intended Audience :: Developers
License :: OSI Approved :: Apache Software License
Operating System :: OS Independent
Programming Language :: Python :: 2.6
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3.3
Programming Language :: Python :: 3.4
Programming Language :: Python :: 3.5
Programming Language :: Python :: 3.6
Programming Language :: Python :: Implementation :: CPython
Programming Language :: Python :: Implementation :: PyPy
Topic :: Software Development :: Quality Assurance
Topic :: Software Development :: Testing
Development Status :: 5 - Production/Stable
"""

setup(
    name='unittest-mixins',
    version='1.0',
    description='Helpful mixins for unittest classes',
    author='Ned Batchelder',
    author_email='ned@nedbatchelder.com',
    url='https://github.com/nedbat/unittest-mixins',
    packages=['unittest_mixins'],
    install_requires=[
        'six >= 1.4.0',
    ],
    license='Apache 2.0',
    classifiers=classifiers.splitlines(),
)
