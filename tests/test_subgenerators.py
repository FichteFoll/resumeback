import pytest

from resumeback import send_self

from . import CustomError, defer, wait_until_finished, State


def test_subgenerator_next():
    ts = State()

    def subgenerator(this):
        yield defer(this.next)
        ts.run = True

    @send_self
    def func(this):
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
    def func(this):
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
    def func(this):
        yield from subgenerator(this)

    wrapper = func()
    wait_until_finished(wrapper)
    assert ts.run


def test_subgenerator_repurpose():
    ts = State()
    val = 1234

    @send_self
    def func2(this):
        assert (yield defer(this.send, val)) == val
        return val + 2

    @send_self
    def func(this):
        ret = yield from func2.func(this)
        assert ret == val + 2
        ts.run = True

    wrapper = func()
    wait_until_finished(wrapper)
    assert ts.run
