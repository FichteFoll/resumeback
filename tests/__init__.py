import threading
import time


DEFAULT_SLEEP = 0.01


class CustomError(Exception):
    pass


def defer(callback, *args, **kwargs):
    sleep = kwargs.pop('sleep', DEFAULT_SLEEP)
    expected_return = kwargs.pop('expected_return', None)
    call = kwargs.pop('call', True)

    def func():
        time.sleep(sleep)
        if call:
            assert expected_return == callback(*args, **kwargs)
        else:
            print("generator is not re-called")

    t = threading.Thread(target=func)
    t.start()


def wait_until_finished(wrapper, timeout=1, sleep=DEFAULT_SLEEP):

    start_time = time.time()
    while time.time() < start_time + timeout:
        # Relies on .has_terminated, but shouldn't be a problem
        if wrapper.has_terminated():
            return
        time.sleep(sleep)
    else:
        raise RuntimeError("Has not been collected within %ss" % timeout)


class State(object):
    def __init__(self):
        self.counter = 0
        self.run = False

    def inc(self):
        self.counter += 1
