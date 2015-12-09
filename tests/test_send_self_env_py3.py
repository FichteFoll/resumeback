import pytest

from resumeback import send_self

from . import CustomError


class TestSendSelfEnvironment(object):

    def test_not_catch_stopiteration_value(self):
        val = id(self) + 100

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
