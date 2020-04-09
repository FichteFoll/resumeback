from __future__ import print_function

import time
import weakref

from resumeback import send_self, StrongGeneratorWrapper, GeneratorWrapper

from . import defer, State


def test_constructors():
    def func():
        yield  # pragma: no cover
    generator = func()
    wrappers = [StrongGeneratorWrapper(generator),
                GeneratorWrapper(weakref.ref(generator))]

    for wrapper in wrappers:
        assert type(wrapper.weak_generator) is weakref.ref
        assert wrapper.weak_generator() is generator
        assert wrapper.catch_stopiteration is True
        assert wrapper.debug is False


def test_equal():
    def func():
        yield  # pragma: no cover
    generator = func()
    assert (StrongGeneratorWrapper(generator)
            == StrongGeneratorWrapper(generator))
    assert (GeneratorWrapper(weakref.ref(generator))
            == GeneratorWrapper(weakref.ref(generator)))

    assert (StrongGeneratorWrapper(generator)
            != GeneratorWrapper(weakref.ref(generator)))


def test_with_weak_ref():
    # Also checks preservance of weak_generator object
    ts = State()

    # Note that `weakref.ref(obj) is weakref.ref(obj)`
    # always holds true,
    # unless you specify a callback parameter
    # for either of the constructors.
    # However, even then they compare equal.
    @send_self(finalize_callback=print)
    def func(this):
        thises = [
            this,
            this.with_weak_ref(),
            this.with_strong_ref().with_weak_ref(),
            this.with_strong_ref().with_strong_ref().with_weak_ref(),
            this()()
        ]
        comp_ref = GeneratorWrapper(weakref.ref(this.generator))
        for i, that in enumerate(thises):
            assert type(that) is GeneratorWrapper, i
            assert that == this

            assert that.weak_generator is this.weak_generator
            assert comp_ref.weak_generator is not that.weak_generator
            assert comp_ref.weak_generator == that.weak_generator
        ts.run = True
        if False:  # Turn into a generator function
            yield

    func()
    assert ts.run


def test_with_strong_ref():
    ts = State()

    # See test_with_weak_ref
    @send_self(finalize_callback=print)
    def func(this):
        this_strong = this.with_strong_ref()
        thises = [
            this_strong,
            this_strong.with_strong_ref(),
            this_strong.with_weak_ref().with_strong_ref(),
            this_strong.with_weak_ref().with_weak_ref().with_strong_ref(),
            this_strong()()
        ]
        comp_ref = StrongGeneratorWrapper(this.generator)
        for i, that in enumerate(thises):
            assert type(that) is StrongGeneratorWrapper, i
            assert that == this_strong

            assert that.weak_generator is this.weak_generator
            assert comp_ref.weak_generator is not that.weak_generator
            assert comp_ref.weak_generator == that.weak_generator
        del thises
        del comp_ref
        ts.run = True
        if False:  # Turn into a generator function
            yield

    func()
    assert ts.run


def test_has_terminated_simple():
    ts = State()

    @send_self
    def func(_):
        ts.run = True
        if False:  # Turn into a generator function
            yield

    assert func().has_terminated()
    assert ts.run


def test_has_terminated():
    ts = State()

    def cb(this):
        assert not this.has_terminated()
        this.send_wait(True)

    @send_self
    def func2(this):
        assert not this.has_terminated()

        ts.run = yield defer(cb, this, sleep=0)
        yield

    wrapper = func2()
    time.sleep(0.1)
    assert ts.run

    assert not wrapper.has_terminated()
    wrapper.next()
    assert wrapper.has_terminated()
