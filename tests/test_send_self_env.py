import pytest

from resumeback import (
    send_self,
    send_self_return,
    WeakGeneratorWrapper,
    StrongGeneratorWrapper
)
from random import random

from . import CustomError, State


def test_wrapper_type():
    ts = State()

    @send_self
    def func():
        this = yield
        assert type(this) is WeakGeneratorWrapper
        ts.run = True

    assert type(func() is StrongGeneratorWrapper)
    assert ts.run


def test_send_self_return():
    ts = State()
    val = 123 + random()

    @send_self_return
    def func():
        this = yield val
        assert type(this) is WeakGeneratorWrapper
        ts.run = True

    assert func() == val
    assert ts.run


def test_wrapping():
    def func():
        """generic docstring"""
        yield  # pragma: no cover

    attributes = ["__%s__" % a
                  for a in 'doc,name,module,annotations'.split(',')]

    for cls in (send_self,       send_self_return,
                send_self(True), send_self_return(True)):
        wrapped = cls(func)
        for attr in attributes:
            if hasattr(wrapped, attr):
                assert getattr(wrapped, attr) == getattr(func, attr)

        if hasattr(wrapped, '__wrapped__'):
            assert wrapped.__wrapped__ is func


def test_not_catch_stopiteration():
    @send_self(catch_stopiteration=False)
    def func():
        yield
        try:
            yield
        except CustomError:
            pass
        # Raises StopIteration here

    for meth, args in [('next',  []),
                       ('send',  [11]),
                       ('throw', [CustomError])]:
        w = func()
        with pytest.raises(StopIteration):
            getattr(w, meth)(*args)


def test_not_catch_stopiteration_value():
    val = random() + 100

    @send_self(catch_stopiteration=False)
    def func():
        yield
        try:
            yield
        except CustomError:
            pass
        return val  # Raises StopIteration here

    for meth, args in [('next',  []),
                       ('send',  [val + 1]),
                       ('throw', [CustomError])]:
        w = func()
        try:
            getattr(w, meth)(*args)
        except StopIteration as si:
            assert si.value == val
        else:
            pytest.fail("Did not raise")


def test_finalize_callback():
    ts = State()
    ts.called = 0
    ts.wref = None

    def cb(ref):
        assert ref is ts.wref
        assert ref() is None
        ts.called += 1

    @send_self(finalize_callback=cb)
    def func():
        this = yield
        ts.wref = this.weak_generator
        ts.called += 1
        # Now, terminate and let gc do its work

    func()
    assert ts.called == 2


def test_cleanup_return():
    @send_self
    def func():
        yield
        # implicit return

    ref = func().weak_generator
    assert ref() is None


def test_cleanup_yield():
    @send_self
    def func():
        yield
        yield

    ref = func().weak_generator
    assert ref() is None


def test_yield_return():
    val = ("const", random())

    @send_self_return
    def func():
        yield val

    assert val == func()


def test_parameter():
    ts = State()
    val = ("const", random())

    @send_self
    def func(param):
        yield
        assert param == val
        ts.run = True

    func(val)
    assert ts.run


@pytest.mark.parametrize(
    'error, func, args, kwargs',
    [
        # "func" arg
        (ValueError, test_parameter, [], {}),
        (ValueError, lambda x: x ** 2, [], {}),
        (ValueError, type, [], {}),
        # "both" args
        (TypeError, None, [type, 1], {}),
        # send_self args
        (TypeError, None, [1], {}),
        (TypeError, None, ["str"], {}),
        (TypeError, None, [], {'catch_stopiteration': 1}),
        (TypeError, None, [], {'finalize_callback': 1}),
        (TypeError, None, [], {'finalize_callback': False}),
        (TypeError, None, [], {'debug': 1}),
        # "delayed" func
        (TypeError, type, [], {'catch_stopiteration': 1}),
        (ValueError, type, [], {'catch_stopiteration': True}),
        (RuntimeError, 1, [], {'catch_stopiteration': True}),
    ]
)
def test_bad_arguments(error, func, args, kwargs):

    with pytest.raises(error):
        if args or kwargs:
            ss = send_self(*args, **kwargs)
        else:
            ss = send_self

        assert func is not None  # Otherwise should have raised by now
        ss(func)
