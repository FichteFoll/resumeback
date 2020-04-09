import pytest

from resumeback import send_self

from . import CustomError, defer, wait_until_finished, State


def test_subgenerator_next():
    ts = State()

    def subgenerator(this):
        yield defer(this.next)
        ts.run = True

    @send_self
    def func():
        this = yield
        yield from subgenerator(this)

    wrapper = func()
    wait_until_finished(wrapper)
    assert ts.run


def test_subgenerator_send():
    ts = State()
    val = 123

    def subgenerator(this):
        assert (yield defer(this.send, val)) == val
        ts.run = True

    @send_self
    def func():
        this = yield
        yield from subgenerator(this)

    wrapper = func()
    wait_until_finished(wrapper)
    assert ts.run


def test_subgenerator_throw():
    ts = State()

    def subgenerator(this):
        with pytest.raises(CustomError):
            yield defer(this.throw, CustomError)
        ts.run = True

    @send_self
    def func():
        this = yield
        yield from subgenerator(this)

    wrapper = func()
    wait_until_finished(wrapper)
    assert ts.run