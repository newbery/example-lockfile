import contextlib
import fcntl
import functools
import os
import time

_shared = fcntl.LOCK_SH | fcntl.LOCK_NB
_exclusive = fcntl.LOCK_EX | fcntl.LOCK_NB


class LockError(Exception):
    """
    Couldn't get a lock
    """


class LockFile:
    """
    The basic class primitive for generating locks.
    """
    _f = None

    def __init__(self, path, shared=False, cleanup=True):
        f = open(path, 'a')
        try:
            fcntl.flock(f.fileno(), _shared if shared else _exclusive)
        except IOError:
            f.close()
            raise LockError("Couldn't lock %r" % f.name)
        self._f = f
        self.path = path
        self.shared = shared
        self.cleanup = cleanup

    def close(self):
        if self._f is not None:
            if self.cleanup and self.shared:
                # remove only if there are no other shared locks
                try:
                    fcntl.flock(self._f.fileno(), _exclusive)
                except IOError:
                    pass
                else:
                    os.remove(self.path)
            elif self.cleanup:
                os.remove(self.path)

            # closing the file handle releases the lock
            self._f.close()
            self._f = None


@contextlib.contextmanager
def lockfile(path, max_retries=10, retry_delay=1, shared=False, error=None):
    """
    A context manager to generate a lockfile.  Yields `None` if lock cannot
    be obtained within the given parameters

    The `shared` flag is used to signal that a shared non-exclusive lock
    should be acquired. A shared lock prevents exclusive locks but not
    additional shared locks.  An exclusive lock prevents shared locks.

    The `error` argument is used to define an error class or instance that
    is raised, instead of returning None, when a lock cannot be obtained.

    Usage:

      with lockfile(path) as lock:
        if lock is None:
            ... do something
        else:
            ... do something else

    """
    tries = 1
    max_tries = 1 + max_retries
    path = path + '.lock'

    lock = None
    while lock is None and tries <= max_tries:
        try:
            lock = LockFile(path, shared=shared)
        except LockError:
            tries += 1
            if tries <= max_tries:
                time.sleep(retry_delay)

    try:
        if error and lock is None:
            raise error
        yield lock
    finally:
        if lock is not None:
            lock.close()


def lockfunc(path=None, max_retries=10, retry_delay=1,
             shared=False, marker=None, error=None):
    """
    Decorator to delay a function call until a file lock is obtained.
    If lock cannot be obtained within the given parameters and `error` is set,
    raises the error class defined by `error`, otherwise returns `marker` value

    The `shared` flag is used to signal that a shared non-exclusive lock
    should be acquired. A shared lock prevents exclusive locks but not
    additional shared locks.  An exclusive lock prevents shared locks.

    Usage (short version):

        lockfunc(path)(myfunction)(*args, **kwargs)

    Usage (long version):

        lock = lockfunc(path)         # 1. Instantiate decorator
        myfunction = lock(myfunction) # 2. Decorate myfunction
        myfunction(*args, **kwargs)   # 3. Call decorated myfunction

    Usage (`@lockfunc` version):

        @lockfunc()
        def myfunction(path, *args, **kwargs):
            ...
        myfunction(path, *args, **kwargs)

    The original non-locked function can still be accessed:

        orig_func = myfunction._func

    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _path = path or args[0]
            with lockfile(
                    _path, max_retries, retry_delay, shared, error) as lock:
                if lock is None:
                    return marker
                return func(*args, **kwargs)
        wrapper._func = func
        return wrapper
    return decorator
