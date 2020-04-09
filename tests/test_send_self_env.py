import pytest

from resumeback import (
    send_self,
    GeneratorWrapper,
    StrongGeneratorWrapper
)
from random import random

from . import CustomError, State


def test_wrapper_type():
    ts = State()

    @send_self
    def func(this):
        assert type(this) is GeneratorWrapper
        ts.run = True
        yield

    assert type(func() is StrongGeneratorWrapper)
    assert ts.run


def test_send_self_return():
    ts = State()
    val = 123 + random()

    def func():
        @send_self
        def internal(this):
            assert type(this) is GeneratorWrapper
            ts.run = True
            yield
        internal()
        return val

    assert func() == val
    assert ts.run


def test_wrapping():
    def func():
        """generic docstring"""
        yield  # pragma: no cover

    attributes = ["__%s__" % a
                  for a in 'doc,name,module,annotations'.split(',')]

    for deco in [send_self, send_self(catch_stopiteration=True)]:
        wrapped = deco(func)
        for attr in attributes:
            if hasattr(wrapped, attr):
                assert getattr(wrapped, attr) == getattr(func, attr)

        if hasattr(wrapped, '__wrapped__'):
            assert wrapped.__wrapped__ is func


def test_not_catch_stopiteration():
    @send_self(catch_stopiteration=False)
    def func(_):
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


@pytest.mark.parametrize(
    'method, args, value',
    [
        ('next', [], None),
        ('send', ["abc"], "abc"),
        ('throw', [CustomError, True], True),
    ]
)
def test_not_catch_stopiteration_value(method, args, value):

    @send_self(catch_stopiteration=False, debug=True)
    def func(_):
        try:
            return (yield)
        except CustomError as e:
            return e.args[0]

    w = func()
    with pytest.raises(StopIteration) as exc:
        getattr(w, method)(*args)
    assert exc.value.value == value


def test_finalize_callback():
    ts = State()
    ts.called = 0
    ts.wref = None

    def cb(ref):
        assert ref is ts.wref
        assert ref() is None
        ts.called += 1

    @send_self(finalize_callback=cb)
    def func(this):
        ts.wref = this.weak_generator
        ts.called += 1
        # Now, terminate and let gc do its work
        if False:  # Turn into a generator function
            yield

    func()
    assert ts.called == 2


def test_cleanup_return():
    @send_self
    def func(_):
        yield
        # implicit return

    ref = func().weak_generator
    assert ref() is None


def test_cleanup_yield():
    @send_self
    def func(_):
        yield

    ref = func().weak_generator
    assert ref() is None


def test_parameter():
    ts = State()
    val = ("const", random())

    @send_self
    def func(_, param):
        assert param == val
        ts.run = True
        if False:  # Turn into a generator function
            yield

    func(val)
    assert ts.run


@pytest.mark.parametrize(
    'error, func, args, kwargs',
    [
        # "func" arg
        (ValueError, test_parameter, [], {}),
        (ValueError, lambda x: x ** 2, [], {}),
        (ValueError, type, [], {}),
        (TypeError, False, [], {}),
        (TypeError, None, [1], {}),
        (TypeError, None, ["str"], {}),
        # too many args
        (TypeError, None, [type, 1], {}),
        # send_self args
        (TypeError, None, [], {'catch_stopiteration': 1}),
        (TypeError, None, [], {'finalize_callback': 1}),
        (TypeError, None, [], {'finalize_callback': False}),
        (TypeError, None, [], {'debug': 1}),
        # "delayed" func
        (TypeError, type, [], {'catch_stopiteration': 1}),
        (ValueError, type, [], {'catch_stopiteration': True}),
        (TypeError, 1, [], {'catch_stopiteration': True}),
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
