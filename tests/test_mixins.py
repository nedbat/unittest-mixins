# -*- coding: utf-8 -*-
# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/unittest-mixins/blob/master/NOTICE.txt

"""Tests that our test infrastructure is really working!"""

import os
import re
import textwrap
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import six

from unittest_mixins import EnvironmentAwareMixin, TempDirMixin, DelayedAssertionMixin


class TempDirMixinTest(TempDirMixin, unittest.TestCase):
    """Test the methods in TempDirMixin."""

    def file_text(self, fname):
        """Return the text read from a file."""
        with open(fname, "rb") as f:
            return f.read().decode('ascii')

    def test_make_file(self):
        # A simple file.
        self.make_file("fooey.boo", "Hello there")
        self.assertEqual(self.file_text("fooey.boo"), "Hello there")
        # A file in a sub-directory
        self.make_file("sub/another.txt", "Another")
        self.assertEqual(self.file_text("sub/another.txt"), "Another")
        # A second file in that sub-directory
        self.make_file("sub/second.txt", "Second")
        self.assertEqual(self.file_text("sub/second.txt"), "Second")
        # A deeper directory
        self.make_file("sub/deeper/evenmore/third.txt")
        self.assertEqual(self.file_text("sub/deeper/evenmore/third.txt"), "")

    def test_make_file_newline(self):
        self.make_file("unix.txt", "Hello\n")
        self.assertEqual(self.file_text("unix.txt"), "Hello\n")
        self.make_file("dos.txt", "Hello\n", newline="\r\n")
        self.assertEqual(self.file_text("dos.txt"), "Hello\r\n")
        self.make_file("mac.txt", "Hello\n", newline="\r")
        self.assertEqual(self.file_text("mac.txt"), "Hello\r")

    def test_make_file_non_ascii(self):
        self.make_file("unicode.txt", "tabblo: «ταБЬℓσ»")
        with open("unicode.txt", "rb") as f:
            text = f.read()
        self.assertEqual(
            text,
            b"tabblo: \xc2\xab\xcf\x84\xce\xb1\xd0\x91\xd0\xac\xe2\x84\x93\xcf\x83\xc2\xbb"
        )


class EnvironmentAwareMixinTest(EnvironmentAwareMixin, unittest.TestCase):
    """Tests of test_helpers.EnvironmentAwareMixin."""

    def setUp(self):
        super(EnvironmentAwareMixinTest, self).setUp()

        # Find a pre-existing environment variable.
        # Not sure what environment variables are available in all of our
        # different testing environments, so try a bunch.
        for envvar in ["HOME", "HOMEDIR", "USER", "SYSTEMDRIVE", "TEMP"]:   # pragma: no branch
            if envvar in os.environ:                                        # pragma: no branch
                self.envvar = envvar
                self.original_text = os.environ[envvar]
                break

    def test_setting_and_cleaning_existing_env_vars(self):
        self.assertNotEqual(self.original_text,  "Some Strange Text")

        # Change the environment.
        self.set_environ(self.envvar, "Some Strange Text")
        self.assertEqual(os.environ[self.envvar],  "Some Strange Text")

        # Do the clean ups early.
        self.doCleanups()

        # The environment should be restored.
        self.assertEqual(os.environ[self.envvar], self.original_text)

    def test_setting_and_cleaning_existing_env_vars_twice(self):
        self.assertNotEqual(self.original_text,  "Some Strange Text")

        # Change the environment.
        self.set_environ(self.envvar, "Some Strange Text")
        self.assertEqual(os.environ[self.envvar],  "Some Strange Text")

        # Change the environment again.
        self.set_environ(self.envvar, "Some Other Thing")
        self.assertEqual(os.environ[self.envvar],  "Some Other Thing")

        # Do the clean ups early.
        self.doCleanups()

        # The environment should be restored.
        self.assertEqual(os.environ[self.envvar], self.original_text)

    def test_setting_and_cleaning_nonexisting_env_vars(self):
        self.assertNotIn("XYZZY_PLUGH", os.environ)

        # Change the environment.
        self.set_environ("XYZZY_PLUGH", "Vogon")

        self.assertEqual(os.environ["XYZZY_PLUGH"], "Vogon")

        # Do the clean ups early.
        self.doCleanups()

        # The environment should be restored.
        self.assertNotIn("XYZZY_PLUGH", os.environ)


class DelayedAssertionMixinTest(DelayedAssertionMixin, unittest.TestCase):
    """Test the `delayed_assertions` method."""

    def test_two_delayed_assertions(self):
        # Two assertions can be shown at once:
        msg = re.escape(textwrap.dedent("""\
            2 failed assertions:
            'x' != 'y'
            - x
            + y

            'w' != 'z'
            - w
            + z
            """))
        with six.assertRaisesRegex(self, AssertionError, msg):
            with self.delayed_assertions():
                self.assertEqual("x", "y")
                self.assertEqual("w", "z")

    def test_only_one_fails(self):
        # It's also OK if only one fails:
        msg = re.escape(textwrap.dedent("""\
            'w' != 'z'
            - w
            + z
            """))
        with six.assertRaisesRegex(self, AssertionError, msg):
            with self.delayed_assertions():
                self.assertEqual("x", "x")
                self.assertEqual("w", "z")

    def test_non_assert_error(self):
        # If an error happens, it gets reported immediately, no special
        # handling:
        with self.assertRaises(ZeroDivisionError):
            with self.delayed_assertions():
                self.assertEqual("x", "y")
                self.assertEqual("w", 1/0)

    def test_no_problem_at_all(self):
        # If all assert pass, then all is well:
        with self.delayed_assertions():
            self.assertEqual("x", "x")
            self.assertEqual("y", "y")
