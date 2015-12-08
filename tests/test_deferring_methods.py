import time

import pytest

from send_self import (
    send_self,
    WaitTimeoutError
)

from . import CustomError, defer, wait_until_finished


class TestSendSelfDeferring(object):

    def test_next(self):
        run = False

        @send_self
        def func():
            nonlocal run
            this = yield
            yield defer(this.next)
            run = True

        wait_until_finished(func(), defer_calls=1)
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

        wait_until_finished(func(), defer_calls=1)
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

        wait_until_finished(func())
        assert run

    def test_throw_return(self):
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

    def test_close(self):
        run = 0

        @send_self
        def func():
            nonlocal run
            this = yield
            run = 1
            yield defer(this.close)
            run = 2

        wrapper = func()
        wait_until_finished(wrapper)
        assert run == 1

    def test_close_generatorexit(self):
        run = 0

        def cb(this):
            nonlocal run
            with pytest.raises(RuntimeError):
                this.close()
            run += 1
            this.next()

        @send_self
        def func():
            nonlocal run
            this = yield
            run += 1
            with pytest.raises(GeneratorExit):
                yield defer(cb, this())
            yield
            run += 1

        wrapper = func().with_weak_ref()
        wait_until_finished(wrapper)
        assert run == 3

    def test_close_garbagecollected(self):
        run = False

        @send_self
        def func():
            nonlocal run
            yield
            with pytest.raises(GeneratorExit):
                yield
            run = True

        wrapper = func().with_weak_ref()
        wait_until_finished(wrapper)
        assert run

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

        wrapper = func()
        wait_until_finished(wrapper)
        assert run

        with pytest.raises(RuntimeError):
            wrapper.next_wait()
        with pytest.raises(RuntimeError):
            wrapper.send_wait(1)
        with pytest.raises(RuntimeError):
            wrapper.throw_wait(CustomError)

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

        wait_until_finished(func())
        assert run

    def test_wait_timeout2(self):
        run = False
        timeouts = range(1, 18, 8)

        @send_self
        def func(timeout):
            nonlocal run
            this = yield
            start = time.time()
            with pytest.raises(WaitTimeoutError):
                this.next_wait(timeout=timeout)
            assert time.time() - start > timeout
            run = True

        for timeout in timeouts:
            wait_until_finished(func(timeout / 100.0))
            assert run
            run = False

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

        wait_until_finished(func())
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

            timeout = 0.3
            t1.join(timeout)
            t2.join(timeout)
            t3.join(timeout)
            assert not t1.is_alive()
            assert not t2.is_alive()
            assert not t3.is_alive()
            run = True

        func()
        assert run
