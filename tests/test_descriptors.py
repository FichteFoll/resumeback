import pytest

from resumeback import send_self

from . import defer, wait_until_finished, State


def test_method():
    class A:
        @send_self
        def method(self, this, param):
            yield defer(this.next)
            assert self.__class__ is A
            self.param = param

    a = A()
    wait_until_finished(a.method(123))
    assert a.param == 123


def test_classmethod():
    ts = State()

    class B:
        @classmethod
        @send_self
        def clsmethod(this, cls, param):
            yield defer(this.next)
            assert cls is B
            ts.run = param

    b = B()
    wait_until_finished(b.clsmethod(123))
    assert ts.run == 123


def test_staticmethod():
    ts = State()

    class C:
        @staticmethod
        @send_self
        def stcmethod(this, param):
            yield defer(this.next)
            ts.run = param

    c = C()
    wait_until_finished(c.stcmethod(123))
    assert ts.run == 123


def test_classmethod_wrong_order():
    with pytest.raises(ValueError, match=r"classmethod"):
        class C:
            @send_self
            @classmethod
            def clsmethod(_, cls, param):
                yield


def test_staticmethod_wrong_order():
    with pytest.raises(ValueError, match=r"staticmethod"):
        class C:
            @send_self
            @staticmethod
            def stcmethod(_, param):
                yield
