import threading
import time


DEFAULT_SLEEP = 0.01


class CustomError(Exception):
    pass


def defer(callback, *args, sleep=DEFAULT_SLEEP, expected_return=None, call=True, **kwargs):

    def func():
        time.sleep(sleep)
        if call:
            assert expected_return == callback(*args, **kwargs)
        else:
            print("generator is not re-called")

    t = threading.Thread(target=func)
    t.start()


def wait_until_finished(wrapper, timeout=1, sleep=DEFAULT_SLEEP, defer_calls=1):
    if not timeout:
        timeout = defer_calls * DEFAULT_SLEEP + 1

    ref = wrapper.weak_generator
    start_time = time.time()
    while time.time() < start_time + timeout:
        if wrapper.has_terminated():
            return
        time.sleep(sleep)
    else:
        if ref() is None:
            return
        raise RuntimeError("Has not been collected within %ss" % timeout)
