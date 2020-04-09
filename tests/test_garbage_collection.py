import gc
import sys

import pytest

from resumeback import send_self

from . import defer, wait_until_finished, State


def test_normal_termination():
    ts = State()

    @send_self
    def func(_):
        ts.run = True
        if False:  # Turn into a generator function
            yield

    wrapper = func().with_weak_ref()
    assert ts.run
    assert wrapper.generator is None


def test_deferred_termination():
    ts = State()

    @send_self
    def func(this):
        yield defer(this.next)
        ts.run = True

    wrapper = func().with_weak_ref()
    wait_until_finished(wrapper)
    assert ts.run
    assert wrapper.generator is None


def test_weakref_suspended():
    ts = State()

    @send_self
    def func(_):
        ts.run = True
        yield
        ts.run = False

    wrapper = func().with_weak_ref()
    assert ts.run
    assert wrapper.generator is None


def test_weakref_suspended_deferred():
    ts = State()

    @send_self
    def func(this):
        ts.run = True
        yield defer(this.next, call=False)
        ts.run = False

    wrapper = func().with_weak_ref()
    wait_until_finished(wrapper)
    assert ts.run
    assert wrapper.generator is None


def test_strongref_suspended():
    ts = State()

    @send_self
    def func(_):
        ts.run = True
        yield
        ts.run = False

    wrapper = func()
    # Should not be gc'd
    with pytest.raises(RuntimeError):
        wait_until_finished(wrapper, timeout=0.1)
    assert ts.run
    assert wrapper.generator is not None

    # Assert proper functionality
    wrapper.next()
    assert not ts.run
    assert wrapper.generator is not None
    assert wrapper.has_terminated()


def test_strongref_suspended_deferred():
    ts = State()

    @send_self
    def func(this):
        ts.run = True
        yield defer(this.next, call=False)
        ts.run = False

    wrapper = func()
    # Should not be gc'd
    with pytest.raises(RuntimeError):
        wait_until_finished(wrapper, timeout=0.1)
    assert ts.run
    assert wrapper.generator is not None


@pytest.mark.xfail(sys.version_info < (3, 4) or sys.version_info >= (3, 7),
                   raises=AssertionError,
                   reason="changes in garbage collection")
def test_circular_strongref_suspended():
    ts = State()

    @send_self
    def func(this):
        this = this()
        ts.run = True
        yield
        ts.run = False

    gc.collect()  # Collect before our own circular reference is created
    wrapper = func().with_weak_ref()
    assert ts.run
    assert wrapper.generator is not None

    after_collected = gc.collect(0)
    # TOCHECK Fails here for Python >= 3.7
    assert after_collected
    # Fails here for Python <= 3.3
    assert wrapper.generator is None
