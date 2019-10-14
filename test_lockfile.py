import os
import shutil
import tempfile
import unittest
import uuid

from .lockfile import LockFile, lockfile, lockfunc


def myfunction():
    return "In my function"


class TestLockfile(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tempdir, str(uuid.uuid4()))

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_lockfile(self):
        """
        `lockfile` should return a LockFile class
        """
        with lockfile(self.path) as lock:
            self.assertIsInstance(lock, LockFile)

    def test_lockfile_failure(self):
        """
        Second attempt to get same lockfile should fail
        """
        with lockfile(self.path) as lock1:
            with lockfile(self.path, max_retries=0) as lock2:
                self.assertIsInstance(lock1, LockFile)
                self.assertIsNone(lock2)

    def test_shared_lockfile(self):
        """
        Shared locks should not block each other but should block
        exclusive locks
        """
        with lockfile(self.path, shared=True) as lock1:
            with lockfile(self.path, max_retries=0, shared=True) as lock2:
                with lockfile(self.path, max_retries=0) as lock3:
                    self.assertIsInstance(lock1, LockFile)
                    self.assertIsInstance(lock2, LockFile)
                    self.assertIsNone(lock3)

    def test_shared_lockfile_failure(self):
        """
        Exclusive locks should block shared locks
        """
        with lockfile(self.path) as lock1:
            with lockfile(self.path, max_retries=0, shared=True) as lock2:
                self.assertIsInstance(lock1, LockFile)
                self.assertIsNone(lock2)

    def test_lockfunc(self):
        """
        `lockfunc` decorator should return result from the original function
        """
        myfunction_withlock = lockfunc(self.path)(myfunction)
        self.assertEqual(myfunction_withlock(), "In my function")

    def test_lockfunc_failure(self):
        """
        `lockfunc`-decorated function should fail if lock is unobtainable
        but should succeed once blocking lock is released.
        """
        myfunction_withlock = lockfunc(self.path, max_retries=0)(myfunction)
        with lockfile(self.path):
            self.assertIsNone(myfunction_withlock())
        self.assertEqual(myfunction_withlock(), "In my function")
