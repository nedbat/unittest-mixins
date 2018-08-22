# -*- coding: utf-8 -*-
# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/unittest-mixins/blob/master/NOTICE.txt

"""Tests that our test infrastructure is really working!"""

import contextlib
import os
import os.path
import re
import shutil
import sys
import tempfile
import textwrap
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import six

from unittest_mixins import (
    change_dir,
    DelayedAssertionMixin,
    EnvironmentAwareMixin,
    ModuleCleaner,
    StdStreamCapturingMixin,
    TempDirMixin,
)


class ChangeDirTest(unittest.TestCase):
    """Test the change_dir decorator."""
    def setUp(self):
        super(ChangeDirTest, self).setUp()
        self.root = tempfile.mkdtemp(prefix="change_dir_test")
        self.addCleanup(shutil.rmtree, self.root)
        self.a_dir = os.path.join(self.root, "a_dir")
        os.mkdir(self.a_dir)
        self.b_dir = os.path.join(self.root, "b_dir")
        os.mkdir(self.b_dir)

    def assert_same_file(self, f1, f2):
        """Assert that f1 and f2 are the same file."""
        self.assertEqual(os.path.realpath(f1), os.path.realpath(f2))

    def assert_different_file(self, f1, f2):
        """Assert that f1 and f2 are not the same file."""
        self.assertNotEqual(os.path.realpath(f1), os.path.realpath(f2))

    def test_change_dir(self):
        here = os.getcwd()
        self.assert_different_file(here, self.root)
        with change_dir(self.root):
            self.assert_same_file(os.getcwd(), self.root)
        self.assert_same_file(os.getcwd(), here)

    def test_change_dir_twice(self):
        here = os.getcwd()
        self.assert_different_file(here, self.root)
        with change_dir(self.root):
            self.assert_same_file(os.getcwd(), self.root)
            os.chdir("a_dir")
            self.assert_same_file(os.getcwd(), self.a_dir)
        self.assert_same_file(os.getcwd(), here)

    def test_change_dir_with_exception(self):
        here = os.getcwd()
        self.assert_different_file(here, self.root)
        try:
            with change_dir(self.root):
                self.assert_same_file(os.getcwd(), self.root)
                raise ValueError("hi")
        except ValueError:
            pass
        self.assert_same_file(os.getcwd(), here)


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
        # Dedenting
        self.make_file("dedented.txt", """\
            Hello
            Bye
            """)
        self.assertEqual(self.file_text("dedented.txt"), "Hello\nBye\n")

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

    def test_make_bytes_file(self):
        self.make_file("binary.dat", bytes=b"\x99\x33\x66hello\0")
        with open("binary.dat", "rb") as f:
            data = f.read()
        self.assertEqual(data, b"\x99\x33\x66hello\0")


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

    def test_deleting(self):
        self.del_environ(self.envvar)
        self.assertNotIn(self.envvar, os.environ)
        self.doCleanups()
        self.assertEqual(os.environ[self.envvar], self.original_text)

    def test_deleting_keeps_things_we_set(self):
        self.set_environ("XYZZY_PLUGH", "Vogon")
        self.del_environ("XYZZY_PLUGH")
        self.assertEqual(os.environ["XYZZY_PLUGH"], "Vogon")
        self.doCleanups()
        self.assertNotIn("XYZZY_PLUGH", os.environ)

    def test_deleting_things_twice(self):
        self.set_environ("XYZZY_PLUGH", "Vogon")
        self.del_environ("XYZZY_PLUGH")
        self.del_environ("XYZZY_PLUGH")
        self.assertEqual(os.environ["XYZZY_PLUGH"], "Vogon")
        self.doCleanups()
        self.assertNotIn("XYZZY_PLUGH", os.environ)

    def test_deleting_nonexistent_things(self):
        self.assertNotIn("XYZZY_PLUGH", os.environ)
        self.del_environ("XYZZY_PLUGH")
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


def run_tests_from_class(klass):
    """Run the unittest tests in klass, and return a TestResult."""
    suite = unittest.TestLoader().loadTestsFromTestCase(klass)
    results = unittest.TestResult()
    suite.run(results)
    return results


def assert_all_passed(results, tests_run=None):
    if tests_run is not None:
        assert results.testsRun == tests_run
    assert results.failures == []
    assert results.errors == []
    assert results.skipped == []


class RunTestsFromClassTest(unittest.TestCase):
    """Tests of the run_tests_from_class function."""

    def test_the_tests_to_test(self):
        class TheTestsToTest(unittest.TestCase):
            """Sample tests to test the run_tests_from_class function."""

            def test_pass(self):
                self.assertEqual(1, 1)

            def test_fail(self):
                self.assertEqual(1, 0)

            def test_skip(self):
                self.skipTest("I feel like it")

            def test_error(self):
                raise Exception("BOOM")

        results = run_tests_from_class(TheTestsToTest)
        self.assertEqual(results.testsRun, 4)
        self.assertEqual(len(results.failures), 1)
        self.assertEqual(results.failures[0][0]._testMethodName, 'test_fail')
        self.assertEqual(len(results.errors), 1)
        self.assertEqual(results.errors[0][0]._testMethodName, 'test_error')
        self.assertEqual(len(results.skipped), 1)
        self.assertEqual(results.skipped[0][0]._testMethodName, 'test_skip')


class StdStreamCapturingMixinTest(unittest.TestCase):
    """Tests of StdStreamCapturingMixin."""

    def test_the_tests_to_test(self):
        class TheTestsToTest(StdStreamCapturingMixin, unittest.TestCase):
            def test_stdout(self):
                sys.stdout.write("Xyzzy")
                self.assertIn("Xyzzy", self.stdout())
                self.assertNotIn("Xyzzy", self.stderr())

            def test_stderr(self):
                sys.stderr.write("Plugh")
                self.assertIn("Plugh", self.stderr())
                self.assertNotIn("Plugh", self.stdout())

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        self.addCleanup(self._cleanup_streams, old_stdout, old_stderr)
        sys.stdout = my_stdout = six.StringIO()
        sys.stderr = my_stderr = six.StringIO()

        results = run_tests_from_class(TheTestsToTest)
        assert_all_passed(results, tests_run=2)

        self.assertIn(my_stdout.getvalue(), "Xyzzy")
        self.assertIn(my_stderr.getvalue(), "Plugh")

    def _cleanup_streams(self, stdout, stderr):
        sys.stdout = stdout
        sys.stderr = stderr


def am_in_tempdir():
    """Are we currently in a temp directory?"""
    return os.path.samefile(
        os.path.dirname(os.getcwd()),
        tempfile.gettempdir()
    )


class ClassBehaviorTest(unittest.TestCase):

    def get_behavior(self, klass):
        behavior = TempDirMixin._class_behaviors.pop(klass)
        return behavior

    def run_and_get_behavior(self, klass):
        """Get the behavior record, and remove it so the process doesn't report on it."""
        results = run_tests_from_class(klass)
        assert_all_passed(results)
        return self.get_behavior(klass)

    def test_tests_are_in_distinct_temp_dirs(self):
        the_dirs = set()

        class _AFewTests(TempDirMixin, unittest.TestCase):
            temp_dir_prefix = "Prefix6_"

            def test_one(self):
                the_dirs.add(os.getcwd())
                assert am_in_tempdir()
                self.make_file("fooey.boo", "Hello there")

            def test_two(self):
                the_dirs.add(os.getcwd())
                assert am_in_tempdir()

            def test_three(self):
                the_dirs.add(os.getcwd())
                assert am_in_tempdir()

            def test_four_errors(self):
                the_dirs.add(os.getcwd())
                assert am_in_tempdir()
                raise Exception("Boom")

            def test_five_fails(self):
                the_dirs.add(os.getcwd())
                assert am_in_tempdir()
                assert 1 == 0

            def test_six(self):
                the_dirs.add(os.getcwd())
                assert am_in_tempdir()

        # This strange way of making the test class is because id() for nested
        # classes changed in 3.5: it named these tests ClassBehaviorTest
        # instead of AFewTests. Making a subclass like this avoids the nesting,
        # which we are only doing here so that the test runner won't run the
        # tests when we don't want it to, and so the class will have access to
        # the_dirs.
        AFewTests = type("AFewTests", (_AFewTests,), {})

        assert not am_in_tempdir()
        original_curdir = os.getcwd()

        results = run_tests_from_class(AFewTests)
        self.assertEqual(results.testsRun, 6)
        self.assertEqual(len(results.errors), 1)
        self.assertEqual(results.errors[0][0]._testMethodName, 'test_four_errors')
        self.assertEqual(len(results.failures), 1)
        self.assertEqual(results.failures[0][0]._testMethodName, 'test_five_fails')

        # We should have six distinct temp dirs.
        self.assertEqual(len(the_dirs), 6)

        # Get the number suffixes
        suffixes = [re.search(r"\d+$", d).group() for d in the_dirs]
        self.assertTrue(all(len(s) == 8 for s in suffixes))
        self.assertTrue(len(set(suffixes)) == 6)

        # The directories should use our prefix, and the test name.
        tempdir = os.path.realpath(tempfile.gettempdir())
        self.assertTrue(all(d.startswith(tempdir) for d in the_dirs))
        centers = sorted(d[len(tempdir)+1:-8] for d in the_dirs)
        self.assertEqual(centers, [
            'Prefix6_tests_test_mixins_AFewTests_test_five_fails_',
            'Prefix6_tests_test_mixins_AFewTests_test_four_errors_',
            'Prefix6_tests_test_mixins_AFewTests_test_one_',
            'Prefix6_tests_test_mixins_AFewTests_test_six_',
            'Prefix6_tests_test_mixins_AFewTests_test_three_',
            'Prefix6_tests_test_mixins_AFewTests_test_two_',
        ])

        # And none of them should exist any more.
        for a_dir in the_dirs:
            self.assertFalse(os.path.exists(a_dir))

        # We should be back where we started.
        self.assertEqual(os.getcwd(), original_curdir)

        # No bad behaviors.
        self.assertIsNone(self.get_behavior(AFewTests).badness())

    def test_made_one_file(self):
        class MadeOneFile(TempDirMixin, unittest.TestCase):
            def test_pass(self):
                self.make_file("fooey.boo", "Hello there")
                assert am_in_tempdir()

        behavior = self.run_and_get_behavior(MadeOneFile)
        self.assertIsNone(behavior.badness())

    def test_made_no_files(self):
        class MadeNoFiles(TempDirMixin, unittest.TestCase):
            def test_pass(self):
                self.assertEqual(1, 1)
                assert am_in_tempdir()

        behavior = self.run_and_get_behavior(MadeNoFiles)
        self.assertEqual(
            behavior.badness(),
            'Inefficient: MadeNoFiles ran 1 tests, 0 made files in a temp directory'
        )

    def test_made_no_files_but_its_ok(self):
        class MadeNoFiles(TempDirMixin, unittest.TestCase):
            no_files_in_temp_dir = True

            def test_pass(self):
                self.assertEqual(1, 1)
                assert am_in_tempdir()

        behavior = self.run_and_get_behavior(MadeNoFiles)
        self.assertIsNone(behavior.badness())

    def test_made_no_files_no_temp_dir(self):
        class MadeNoFilesOK(TempDirMixin, unittest.TestCase):
            run_in_temp_dir = False

            def test_pass(self):
                self.assertEqual(1, 1)
                assert not am_in_tempdir()

        behavior = self.run_and_get_behavior(MadeNoFilesOK)
        self.assertIsNone(behavior.badness())

    def test_made_files_no_temp_dir(self):
        class MadeFilesNoTempDir(TempDirMixin, unittest.TestCase):
            run_in_temp_dir = False

            def test_will_fail(self):
                assert not am_in_tempdir()
                self.make_file("fooey.boo", "Hello there")

        results = run_tests_from_class(MadeFilesNoTempDir)
        self.assertEqual(results.testsRun, 1)
        self.assertEqual(len(results.failures), 1)
        self.assertEqual(results.failures[0][0]._testMethodName, 'test_will_fail')
        self.assertIn(
            "AssertionError: Should only use make_file in temp directories",
            results.failures[0][1]
        )

    def test_skipping_all_tests(self):
        class SkippedAllTests(TempDirMixin, unittest.TestCase):
            def test_skip_1(self):
                self.skipTest("The first skip")

            def test_skip_2(self):
                self.skipTest("The second skip")

        results = run_tests_from_class(SkippedAllTests)
        self.assertEqual(results.testsRun, 2)
        self.assertEqual(len(results.skipped), 2)
        behavior = self.get_behavior(SkippedAllTests)
        self.assertIsNone(behavior.badness())

    def test_keeping_temp_dir(self):
        the_dirs = set()

        class AFewTests(TempDirMixin, unittest.TestCase):
            keep_temp_dir = True

            def test_one(self):
                the_dirs.add(os.getcwd())
                assert am_in_tempdir()
                self.make_file("fooey.boo", "Hello there")

            def test_two(self):
                the_dirs.add(os.getcwd())
                assert am_in_tempdir()

        # We'll be leaving test directories behind, so clean them up ourselves.
        def clean_up():
            for a_dir in the_dirs:
                shutil.rmtree(a_dir)
        self.addCleanup(clean_up)

        original_curdir = os.getcwd()
        results = run_tests_from_class(AFewTests)
        self.assertEqual(results.testsRun, 2)

        # We should have two distinct temp dirs.
        self.assertEqual(len(the_dirs), 2)

        # And all of them should exist.
        for a_dir in the_dirs:
            self.assertTrue(os.path.exists(a_dir))

        # We should be back where we started.
        self.assertEqual(os.getcwd(), original_curdir)


@contextlib.contextmanager
def no_bytecode():
    """Temporarily stop writing bytecode."""
    sys.dont_write_bytecode = True
    try:
        yield
    finally:
        sys.dont_write_bytecode = False


class ModuleAwareMixinTest(TempDirMixin, unittest.TestCase):
    def test_two_tests_get_different_modules(self):
        class MakeAndImportFilesTest(TempDirMixin, unittest.TestCase):
            def test_one(self):
                self.make_file("xyzzy.py", "A = 17")
                import xyzzy
                self.assertEqual(xyzzy.A, 17)

            def test_two(self):
                self.make_file("xyzzy.py", "A = 42")
                import xyzzy
                self.assertEqual(xyzzy.A, 42)

        results = run_tests_from_class(MakeAndImportFilesTest)
        assert_all_passed(results, tests_run=2)

    def test_cleanup_and_reimport(self):
        with no_bytecode():
            self.make_file("xyzzy.py", "A = 17")
            import xyzzy
            self.assertEqual(xyzzy.A, 17)

            self.cleanup_modules()

            self.make_file("xyzzy.py", "A = 42")
            import xyzzy
            self.assertEqual(xyzzy.A, 42)


class ModuleCleanerMixinTest(TempDirMixin, unittest.TestCase):
    def test_module_cleaner(self):
        with no_bytecode():
            cleaner = ModuleCleaner()

            self.make_file("xyzzy.py", "A = 17")
            import xyzzy
            self.assertEqual(xyzzy.A, 17)

            cleaner.cleanup_modules()

            self.make_file("xyzzy.py", "A = 42")
            import xyzzy
            self.assertEqual(xyzzy.A, 42)
