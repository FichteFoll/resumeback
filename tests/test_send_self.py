import gc  # TODO is this actually needed?
import threading
import time

import pytest

# import send_self
from ..send_self import (
    send_self,
    send_self_return,
    WaitTimeoutError,
    WeakGeneratorWrapper,
    StrongGeneratorWrapper
)

# TODO stopiteration return values
# TODO only gc'd when deferred thread terminates and does not call
# TODO not gc'd
# TODO subgenerator shit


default_sleep = 0.1


def defer(callback, *args, sleep=default_sleep, expected_return=None, call=True,
          **kwargs):

    def func():
        time.sleep(sleep)
        if call:
            assert expected_return == callback(*args, **kwargs)
        else:
            print("generator is not re-called")

    t = threading.Thread(target=func)
    t.start()


def wait_until_finished(wrapper, timeout=None, sleep=default_sleep,
                        defer_calls=1):
    # Can not be called with StrongGeneratorWrapper, likely because it will be
    # bound in some frame and thus its reference won't get gc'd when it would
    # otherwise.
    assert type(wrapper) is WeakGeneratorWrapper

    if not timeout:
        timeout = defer_calls * default_sleep + 1

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


class TestGeneratorWrapper(object):
    pass


class TestSendSelfEnvironment(object):
    def test_wrapper_type(self):
        @send_self
        def func():
            this = yield
            assert type(this) is WeakGeneratorWrapper

        assert type(func() is StrongGeneratorWrapper)

    def test_send_self_return(self):
        val = 123 + id(self)

        @send_self_return
        def func():
            nonlocal val
            this = yield val
            assert type(this) is WeakGeneratorWrapper

        assert func() == val

    def test_not_catch_stopiteration(self):
        @send_self(catch_stopiteration=False)
        def func():
            yield
            try:
                yield
            except:
                pass
            # Raises here

        for meth, args in [("next", []),
                           ("send", [11]),
                           ("throw", [ValueError])]:
            w = func()
            with pytest.raises(StopIteration):
                getattr(w, meth)(*args)

    def test_not_catch_stopiteration_value(self):
        val = id(self) + 100

        @send_self(catch_stopiteration=False)
        def func():
            yield
            try:
                yield
            except:
                pass
            return val  # Raises StopIteration here

        for meth, args in [("next", []),
                           ("send", [val + 1]),
                           ("throw", [ValueError])]:
            w = func()
            try:
                getattr(w, meth)(*args)
            except StopIteration as si:
                assert si.value == val
            else:
                pytest.fail("Did not raise")

    def test_finalize_callback(self):
        wref = None
        called = False

        def cb(ref):
            nonlocal called, wref
            assert ref == wref
            assert ref() is None
            called = True

        @send_self(finalize_callback=cb)
        def func():
            nonlocal wref
            this = yield
            wref = this.weak_generator
            # Now, terminate and let gc do its work

        func()
        # gc.collect()  # not needed
        assert called

    def test_cleanup_return(self):
        @send_self
        def func():
            yield
            # implicit return

        ref = func().weak_generator
        # gc.collect()  # not needed
        assert ref() is None

    def test_cleanup_yield(self):
        @send_self
        def func():
            yield
            yield

        ref = func().weak_generator
        # gc.collect()  # not needed
        assert ref() is None

    def test_yield_return(self):
        val = ("const", id(self))

        @send_self_return
        def func():
            yield val

        assert val == func()

    def test_yield_parameter(self):
        val = ("const", id(self))

        @send_self
        def func(param):
            yield
            nonlocal val
            assert param == val

        func(val)

    def generic_gen():
        yield

    @pytest.mark.parametrize(
        ['error', 'func', 'args', 'kwargs'],
        [
            # "func" arg
            (ValueError, test_yield_parameter, [], {}),
            (ValueError, lambda x: x ** 2, [], {}),
            # send_self args
            (TypeError, None, [1], {}),
            (TypeError, None, ["str"], {}),
            (TypeError, None, [], {'catch_stopiteration': 1}),
            (TypeError, None, [], {'finalize_callback': 1}),
            (TypeError, None, [], {'finalize_callback': False}),
            (TypeError, None, [], {'debug': 1}),
        ]
    )
    def test_bad_arguments(self, error, func, args, kwargs):

        with pytest.raises(error):
            if args or kwargs:
                ss = send_self(*args, **kwargs)
            else:
                ss = send_self

            assert func is not None  # Otherwise should have raised by now
            ss(func)


class TestSendSelfDeferring(object):
    def test_next(self):
        run = False

        @send_self
        def func():
            nonlocal run
            this = yield
            yield defer(this.next)
            run = True

        wait_until_finished(func().with_weak_ref(), defer_calls=1)
        assert run

    def test_next_failures(self):
        # TODO test bad arguments for all 3
        @send_self
        def func():
            this = yield
            with pytest.raises(TypeError):
                this.next("argument")

            with pytest.raises(ValueError):
                this.next()  # Generator still running

        func()

    def test_send(self):
        run = False

        @send_self
        def func():
            nonlocal run
            this = yield

            val = 345 + id(func)
            received = yield defer(this.send, val)
            assert received == val
            run = True

        wait_until_finished(func().with_weak_ref(), defer_calls=1)
        assert run

    def test_throw(self):
        run = False

        @send_self
        def func():
            nonlocal run
            this = yield

            val = 345 + id(func)
            defer(this.throw, ValueError, val)
            try:
                yield
                pytest.fail("no exception thrown")
            except ValueError as e:
                assert e.args == (val,)

            run = True

        wait_until_finished(func().with_weak_ref(), defer_calls=1)
        assert run

    def test_throw_return(self):
        val = 2 + id(self)

        @send_self
        def func():
            yield
            try:
                yield
            except ValueError:
                return val

        wrapper = func()
        assert val == wrapper.throw(ValueError)
        wrapper = wrapper.with_weak_ref()  # Allow for gc
        gc.collect()
        assert wrapper.generator is None

    def test_wait(self):
        run = False

        @send_self(debug=True)
        def func():
            nonlocal run
            this = yield

            defer(this.next_wait, sleep=0)
            time.sleep(0.01)
            yield

            defer(this.send_wait, 0, sleep=0)
            time.sleep(0.01)
            yield

            defer(this.throw_wait, ValueError, sleep=0, timeout=0.1)
            time.sleep(0.01)
            with pytest.raises(ValueError):
                yield

            run = True
            yield

        wait_until_finished(func().with_weak_ref(), timeout=3)
        assert run

    def test_wait_timeout(self):
        run = False

        @send_self
        def func():
            nonlocal run
            this = yield

            with pytest.raises(WaitTimeoutError):
                this.next_wait(timeout=0.01)

            with pytest.raises(WaitTimeoutError):
                this.send_wait(0, timeout=0.01)

            with pytest.raises(WaitTimeoutError):
                this.throw_wait(timeout=0.01)

            run = True

        wait_until_finished(func().with_weak_ref())
        assert run

    def test_wait_async(self):
        run = False

        @send_self(debug=True)
        def func():
            nonlocal run
            this = yield

            this.next_wait_async()
            time.sleep(0.1)
            yield

            val = 567 + id(func)
            this.send_wait_async(val)
            time.sleep(0.1)
            received = yield
            assert received == val

            this.throw_wait_async(ValueError, timeout=0.5)
            time.sleep(0.1)
            print(2)
            with pytest.raises(ValueError):
                yield

            run = True
            print("finished")

        wait_until_finished(func().with_weak_ref())
        assert run

    def test_wait_async_timeout(self):
        run = False

        @send_self(debug=True)
        def func():
            nonlocal run
            this = yield

            t1 = this.next_wait_async(timeout=0.01)
            t2 = this.send_wait_async(1, timeout=0.01)
            t3 = this.throw_wait_async(RuntimeError, timeout=0.01)

            time.sleep(0.1)
            assert not t1.is_alive()
            assert not t2.is_alive()
            assert not t3.is_alive()
            run = True

        func()
        assert run
