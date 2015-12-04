import time

import pytest

from ..send_self import (
    send_self,
    WaitTimeoutError
)

from . import CustomError, defer, wait_until_finished


class TestSubgenerators(object):

    def test_subgenerator_next(self):
        run = False

        def subgenerator(this):
            nonlocal run
            yield defer(this.next)
            run = True

        @send_self
        def func():
            nonlocal run
            this = yield
            yield from subgenerator(this)

        wrapper = func()
        wait_until_finished(wrapper)
        assert run

    def test_subgenerator_send(self):
        run = False
        val = 123 + id(self)

        def subgenerator(this):
            nonlocal run, val
            assert (yield defer(this.send, val)) == val
            run = True

        @send_self
        def func():
            nonlocal run
            this = yield
            yield from subgenerator(this)

        wrapper = func()
        wait_until_finished(wrapper)
        assert run

    def test_subgenerator_throw(self):
        run = False

        def subgenerator(this):
            nonlocal run
            with pytest.raises(CustomError):
                yield defer(this.throw, CustomError)
            run = True

        @send_self
        def func():
            nonlocal run
            this = yield
            yield from subgenerator(this)

        wrapper = func()
        wait_until_finished(wrapper)
        assert run
