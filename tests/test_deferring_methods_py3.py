from resumeback import send_self
from . import CustomError


class TestSendSelfDeferring(object):

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
