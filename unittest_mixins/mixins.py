# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/unittest-mixins/blob/master/NOTICE.txt

"""Mixin classes to help make good tests."""

import atexit
import collections
import contextlib
import os
import random
import shutil
import sys
import tempfile
import textwrap
try:
    import unittest2 as unittest
except:
    import unittest

import six


class _Tee(object):
    """A file-like that writes to all the file-likes it has."""

    def __init__(self, *files):
        """Make a `_Tee` that writes to all the files in `files.`"""
        self._files = files
        if hasattr(files[0], "encoding"):
            self.encoding = files[0].encoding

    def write(self, data):
        """Write `data` to all the files."""
        for f in self._files:
            f.write(data)

    def flush(self):
        """Flush the data on all the files."""
        for f in self._files:
            f.flush()

    def getvalue(self):
        """StringIO file-likes have .getvalue()"""
        return self._files[0].getvalue()

    if 0:
        # Use this if you need to use a debugger, though it makes some tests
        # fail, I'm not sure why...
        def __getattr__(self, name):
            return getattr(self._files[0], name)


@contextlib.contextmanager
def change_dir(new_dir):
    """Change directory, and then change back.

    Use as a context manager, it will give you the new directory, and later
    restore the old one.

    """
    old_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield os.getcwd()
    finally:
        os.chdir(old_dir)


@contextlib.contextmanager
def saved_sys_path():
    """Save sys.path, and restore it later."""
    old_syspath = sys.path[:]
    try:
        yield
    finally:
        sys.path = old_syspath


def setup_with_context_manager(testcase, cm):
    """Use a contextmanager to setUp a test case.

    If you have a context manager you like::

        with ctxmgr(a, b, c) as v:
            # do something with v

    and you want to have that effect for a test case, call this function from
    your setUp, and it will start the context manager for your test, and end it
    when the test is done::

        def setUp(self):
            self.v = setup_with_context_manager(self, ctxmgr(a, b, c))

        def test_foo(self):
            # do something with self.v

    """
    val = cm.__enter__()
    testcase.addCleanup(cm.__exit__, None, None, None)
    return val


class ModuleCleaner(object):
    """Remember the state of sys.modules, and provide a way to restore it."""

    def __init__(self):
        self._old_modules = list(sys.modules)

    def cleanup_modules(self):
        """Remove any new modules imported since our construction.

        This lets us import the same source files for more than one test, or
        if called explicitly, within one test.

        """
        for m in [m for m in sys.modules if m not in self._old_modules]:
            del sys.modules[m]


class ModuleAwareMixin(unittest.TestCase):
    """A test case mixin that isolates changes to sys.modules."""

    def setUp(self):
        super(ModuleAwareMixin, self).setUp()

        self._module_cleaner = ModuleCleaner()
        self.addCleanup(self._module_cleaner.cleanup_modules)

    def cleanup_modules(self):
        self._module_cleaner.cleanup_modules()


class SysPathAwareMixin(unittest.TestCase):
    """A test case mixin that isolates changes to sys.path."""

    def setUp(self):
        super(SysPathAwareMixin, self).setUp()
        setup_with_context_manager(self, saved_sys_path())


class EnvironmentAwareMixin(unittest.TestCase):
    """A test case mixin that isolates changes to the environment."""

    def setUp(self):
        super(EnvironmentAwareMixin, self).setUp()

        # Record environment variables that we changed with set_environ.
        self._environ_undos = {}

        self.addCleanup(self._cleanup_environ)

    def set_environ(self, name, value):
        """Set an environment variable `name` to be `value`.

        The environment variable is set, and record is kept that it was set,
        so that `cleanup_environ` can restore its original value.

        """
        if name not in self._environ_undos:
            self._environ_undos[name] = os.environ.get(name)
        os.environ[name] = value

    def _cleanup_environ(self):
        """Undo all the changes made by `set_environ`."""
        for name, value in self._environ_undos.items():
            if value is None:
                del os.environ[name]
            else:
                os.environ[name] = value


class StdStreamCapturingMixin(unittest.TestCase):
    """A test case mixin that captures stdout and stderr."""

    def setUp(self):
        super(StdStreamCapturingMixin, self).setUp()

        # Capture stdout and stderr so we can examine them in tests.
        # nose keeps stdout from littering the screen, so we can safely _Tee
        # it, but it doesn't capture stderr, so we don't want to _Tee stderr to
        # the real stderr, since it will interfere with our nice field of dots.
        old_stdout = sys.stdout
        self.captured_stdout = six.StringIO()
        sys.stdout = _Tee(sys.stdout, self.captured_stdout)

        old_stderr = sys.stderr
        self.captured_stderr = six.StringIO()
        sys.stderr = self.captured_stderr

        self.addCleanup(self._cleanup_std_streams, old_stdout, old_stderr)

    def _cleanup_std_streams(self, old_stdout, old_stderr):
        """Restore stdout and stderr."""
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    def stdout(self):
        """Return the data written to stdout during the test."""
        return self.captured_stdout.getvalue()

    def stderr(self):
        """Return the data written to stderr during the test."""
        return self.captured_stderr.getvalue()


class DelayedAssertionMixin(unittest.TestCase):
    """A test case mixin that provides a `delayed_assertions` context manager.

    Use it like this::

        with self.delayed_assertions():
            self.assertEqual(x, y)
            self.assertEqual(z, w)

    All of the assertions will run.  The failures will be displayed at the end
    of the with-statement.

    NOTE: this only works with some assertions.  These are known to work:

        - `assertEqual(str, str)`

        - `assertMultilineEqual(str, str)`

    """
    def __init__(self, *args, **kwargs):
        super(DelayedAssertionMixin, self).__init__(*args, **kwargs)
        # This mixin only works with assert methods that call `self.fail`.  In
        # Python 2.7, `assertEqual` didn't, but we can do what Python 3 does,
        # and use `assertMultiLineEqual` for comparing strings.
        self.addTypeEqualityFunc(str, 'assertMultiLineEqual')
        self._delayed_assertions = None

    @contextlib.contextmanager
    def delayed_assertions(self):
        """The context manager: assert that we didn't collect any assertions."""
        self._delayed_assertions = []
        old_fail = self.fail
        self.fail = self._delayed_fail
        try:
            yield
        finally:
            self.fail = old_fail
        if self._delayed_assertions:
            if len(self._delayed_assertions) == 1:
                self.fail(self._delayed_assertions[0])
            else:
                self.fail(
                    "{0} failed assertions:\n{1}".format(
                        len(self._delayed_assertions),
                        "\n".join(self._delayed_assertions),
                    )
                )

    def _delayed_fail(self, msg=None):
        """The stand-in for TestCase.fail during delayed_assertions."""
        self._delayed_assertions.append(msg)


def make_file(filename, text="", newline=None):
    """Create a file for testing.

    `filename` is the relative path to the file, including directories if
    desired, which will be created if need be.

    `text` is the content to create in the file, a native string (bytes in
    Python 2, unicode in Python 3).

    If `newline` is provided, it is a string that will be used as the line
    endings in the created file, otherwise the line endings are as provided
    in `text`.

    Returns `filename`.

    """
    text = textwrap.dedent(text)
    if newline:
        text = text.replace("\n", newline)

    # Make sure the directories are available.
    dirs, _ = os.path.split(filename)
    if dirs and not os.path.exists(dirs):
        os.makedirs(dirs)

    # Create the file.
    with open(filename, 'wb') as f:
        if six.PY3:
            text = text.encode('utf8')
        f.write(text)

    return filename


class TempDirMixin(SysPathAwareMixin, ModuleAwareMixin, unittest.TestCase):
    """A test case mixin that creates a temp directory and files in it.

    Includes SysPathAwareMixin and ModuleAwareMixin, because making and using
    temp directories like this will also need that kind of isolation.

    The temp directory is available as self.temp_dir.

    """

    # Our own setting: most of these tests run in their own temp directory.
    # Set this to False in your subclass if you don't want a temp directory
    # created.
    run_in_temp_dir = True

    # Set this if you aren't creating any files with make_file, but still want
    # the temp directory.  This will stop the test behavior checker from
    # complaining.
    no_files_in_temp_dir = False

    def setUp(self):
        super(TempDirMixin, self).setUp()

        if self.run_in_temp_dir:
            # Create a temporary directory.
            self.temp_dir = self._make_temp_dir("test_cover")
            self.chdir(self.temp_dir)

            # Modules should be importable from this temp directory.  We don't
            # use '' because we make lots of different temp directories and
            # nose's caching importer can get confused.  The full path prevents
            # problems.
            sys.path.insert(0, os.getcwd())

        class_behavior = self._class_behavior()
        class_behavior.tests += 1
        class_behavior.temp_dir = self.run_in_temp_dir
        class_behavior.no_files_ok = self.no_files_in_temp_dir

        self.addCleanup(self._check_behavior)

    def _check_behavior(self):
        """Check that we did the right things."""

        class_behavior = self._class_behavior()
        if class_behavior.test_method_made_any_files:
            class_behavior.tests_making_files += 1

    def _make_temp_dir(self, slug="test_cover"):
        """Make a temp directory that is cleaned up when the test is done."""
        name = "%s_%08d" % (slug, random.randint(0, 99999999))
        temp_dir = os.path.join(tempfile.gettempdir(), name)
        os.makedirs(temp_dir)
        self.addCleanup(shutil.rmtree, temp_dir)
        return temp_dir

    def skipTest(self, reason):
        """Skip this test, and give a reason."""
        self._class_behavior().skipped += 1
        super(TempDirMixin, self).skipTest(reason)

    def chdir(self, new_dir):
        """Change directory, and change back when the test is done."""
        old_dir = os.getcwd()
        os.chdir(new_dir)
        self.addCleanup(os.chdir, old_dir)

    def make_file(self, filename, text="", newline=None):
        """Create a file for testing.  See `make_file` for docs."""

        # Tests that call `make_file` should be run in a temp environment.
        assert self.run_in_temp_dir, "Should only use make_file in temp directories"
        self._class_behavior().test_method_made_any_files = True

        return make_file(filename, text, newline)

    # We run some tests in temporary directories, because they may need to make
    # files for the tests. But this is expensive, so we can change per-class
    # whether a temp directory is used or not.  It's easy to forget to set that
    # option properly, so we track information about what the tests did, and
    # then report at the end of the process on test classes that were set
    # wrong.

    class _ClassBehavior(object):
        """A value object to store per-class."""
        def __init__(self):
            self.klass = None
            self.tests = 0
            self.skipped = 0
            self.temp_dir = True
            self.no_files_ok = False
            self.tests_making_files = 0
            self.test_method_made_any_files = False

        def badness(self):
            """Return a string describing bad behavior, or None."""
            bad = ""
            if self.tests <= self.skipped:
                bad = ""
            elif self.temp_dir and self.tests_making_files == 0:
                if not self.no_files_ok:
                    bad = "Inefficient"

            if bad:
                where = "in a temp directory"
                return (
                    "%s: %s ran %d tests, %d made files %s" % (
                        bad,
                        self.klass.__name__,
                        self.tests,
                        self.tests_making_files,
                        where,
                    )
                )

    # Map from class to info about how it ran.
    _class_behaviors = collections.defaultdict(_ClassBehavior)

    @classmethod
    def _report_on_class_behavior(cls):
        """Called at process exit to report on class behavior."""
        for behavior in cls._class_behaviors.values():
            badness = behavior.badness()
            if badness:
                print(badness)

    def _class_behavior(self):
        """Get the ClassBehavior instance for this test."""
        behavior = self._class_behaviors[self.__class__]
        behavior.klass = self.__class__
        return behavior


# When the process ends, find out about bad classes.
atexit.register(TempDirMixin._report_on_class_behavior)
