import time

import pytest

from ..send_self import (
    send_self,
    WaitTimeoutError
)

from . import CustomError, defer, wait_until_finished

# TODO only gc'd when deferred thread terminates and does not call
# TODO gc (*_cleanup)
# TODO subgenerator shit


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
            assert (yield defer(this.send, val)) == val
            assert (yield defer(this.send)) is None
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
            defer(this.throw, CustomError, val)
            try:
                yield
            except CustomError as e:
                assert e.args == (val,)
            else:
                pytest.fail("no exception thrown")

            run = True

        wait_until_finished(func().with_weak_ref(), defer_calls=1)
        assert run

    def test_throw_return(self):
        # TODO split in two (test_throw_cleanup)
        val = 2 + id(self)

        @send_self
        def func():
            yield
            try:
                yield
            except CustomError:
                return val

        wrapper = func()
        assert val == wrapper.throw(CustomError)
        wrapper = wrapper.with_weak_ref()  # Allow for gc
        # gc.collect()  # Not needed
        assert wrapper.generator is None

    def test_close(self):
        run = 0

        def cb(f):
            f.close()

        @send_self
        def func():
            nonlocal run
            this = yield
            run = 1
            # this.close()
            yield defer(this.close)
            run = 2

        wrapper = func()
        wait_until_finished(wrapper)
        assert run == 1
        assert wrapper.has_terminated()

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

            defer(this.throw_wait, CustomError, sleep=0, timeout=0.1)
            time.sleep(0.01)
            with pytest.raises(CustomError):
                yield

            run = True
            yield

        wait_until_finished(func().with_weak_ref(), timeout=1)
        assert run
        # TODO test when terminated

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

            this.throw_wait_async(CustomError, timeout=0.5)
            time.sleep(0.1)
            with pytest.raises(CustomError):
                yield

            run = True

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
