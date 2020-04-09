import time

import pytest

from resumeback import send_self, WaitTimeoutError

from . import CustomError, defer, wait_until_finished, State


def test_next():
    ts = State()

    @send_self
    def func(this):
        yield defer(this.next)
        ts.run = True

    wait_until_finished(func())
    assert ts.run


def test_next_failures():
    @send_self
    def func(this):
        with pytest.raises(TypeError):
            this.next("argument")

        with pytest.raises(ValueError):
            this.next()  # Generator still running
        if False:  # Turn into a generator function
            yield

    func()


def test_send():
    ts = State()

    @send_self
    def func(this):
        val = 345 + id(func)
        assert (yield defer(this.send, val)) == val
        assert (yield defer(this.send)) is None
        ts.run = True

    wait_until_finished(func())
    assert ts.run


def test_throw():
    ts = State()

    @send_self
    def func(this):
        val = 345 + id(func)
        defer(this.throw, CustomError, val)
        try:
            yield
        except CustomError as e:
            assert e.args == (val,)
        else:
            pytest.fail("no exception thrown")

        ts.run = True

    wait_until_finished(func())
    assert ts.run


def test_throw_return():
    val = 2232

    @send_self
    def func(_):
        try:
            yield
        except CustomError:
            return val

    wrapper = func()
    assert val == wrapper.throw(CustomError)


def test_close():
    ts = State()

    @send_self
    def func(this):
        ts.run = True
        yield defer(this.close)
        ts.run = False

    wrapper = func()
    wait_until_finished(wrapper)
    assert ts.run


def test_close_generatorexit():
    ts = State()

    def cb(this):
        with pytest.raises(RuntimeError):
            this.close()
        ts.inc()
        this.next()  # TOCHECK should this run or should the gen close?

    @send_self
    def func(this):
        ts.inc()
        with pytest.raises(GeneratorExit):
            yield defer(cb, this())
        ts.inc()
        yield  # yields and causes RuntimeError to be thrown
        ts.inc()

    wrapper = func().with_weak_ref()
    wait_until_finished(wrapper)
    assert ts.counter == 3


def test_close_garbagecollected():
    ts = State()

    @send_self
    def func(_):
        with pytest.raises(GeneratorExit):
            yield
        ts.run = True

    wrapper = func().with_weak_ref()
    wait_until_finished(wrapper)
    assert ts.run


def test_wait():
    ts = State()

    @send_self(debug=True)
    def func(this):
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

        ts.run = True

    wrapper = func()
    wait_until_finished(wrapper)
    assert ts.run

    with pytest.raises(RuntimeError):
        wrapper.next_wait()
    with pytest.raises(RuntimeError):
        wrapper.send_wait(1)
    with pytest.raises(RuntimeError):
        wrapper.throw_wait(CustomError)


def test_wait_timeout():
    ts = State()

    @send_self
    def func(this):
        with pytest.raises(WaitTimeoutError):
            this.next_wait(timeout=0.01)

        with pytest.raises(WaitTimeoutError):
            this.send_wait(0, timeout=0.01)

        with pytest.raises(WaitTimeoutError):
            this.throw_wait(timeout=0.01)

        ts.run = True
        if False:  # Turn into a generator function
            yield

    wait_until_finished(func())
    assert ts.run


def test_wait_timeout2():
    ts = State()
    timeouts = range(1, 18, 8)

    @send_self
    def func(this, timeout):
        start = time.time()
        with pytest.raises(WaitTimeoutError):
            this.next_wait(timeout=timeout)
        assert time.time() - start > timeout
        ts.run = True
        if False:  # Turn into a generator function
            yield

    for timeout in timeouts:
        wait_until_finished(func(timeout / 100.0))
        assert ts.run
        ts.run = False


def test_wait_async():
    ts = State()

    @send_self(debug=True)
    def func(this):
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

        ts.run = True

    wait_until_finished(func())
    assert ts.run


def test_wait_async_timeout():
    ts = State()

    @send_self(debug=True)
    def func(this):
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
        ts.run = True
        if False:  # Turn into a generator function
            yield

    func()
    assert ts.run
