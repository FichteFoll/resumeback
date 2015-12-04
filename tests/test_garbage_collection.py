import gc

import pytest

from ..send_self import send_self

from . import defer, wait_until_finished


class TestGarbageCollection(object):

    def test_normal_termination(self):
        run = False

        @send_self
        def func():
            nonlocal run
            yield
            run = True

        wrapper = func().with_weak_ref()
        assert run
        assert wrapper.generator is None

    def test_deferred_termination(self):
        run = False

        @send_self
        def func():
            nonlocal run
            this = yield
            yield defer(this.next)
            run = True

        wrapper = func().with_weak_ref()
        wait_until_finished(wrapper)
        assert run
        assert wrapper.generator is None

    def test_weakref_suspended(self):
        run = False

        @send_self
        def func():
            nonlocal run
            yield
            run = True
            yield
            run = False

        wrapper = func().with_weak_ref()
        assert run
        assert wrapper.generator is None

    def test_weakref_suspended_deferred(self):
        run = False

        @send_self
        def func():
            nonlocal run
            this = yield
            run = True
            yield defer(this.next, call=False)
            run = False

        wrapper = func().with_weak_ref()
        wait_until_finished(wrapper)
        assert run
        assert wrapper.generator is None

    def test_strongref_suspended(self):
        run = False

        @send_self
        def func():
            nonlocal run
            yield
            run = True
            yield
            run = False

        wrapper = func()
        # Should not be gc'd
        with pytest.raises(RuntimeError):
            wait_until_finished(wrapper, timeout=0.1)
        assert run
        assert wrapper.generator is not None

        # Assert proper functionality
        wrapper.next()
        assert not run
        assert wrapper.generator is not None
        assert wrapper.has_terminated()

    def test_strongref_suspended_deferred(self):
        run = False

        @send_self
        def func():
            nonlocal run
            this = yield
            run = True
            yield defer(this.next, call=False)
            run = False

        wrapper = func()
        # Should not be gc'd
        with pytest.raises(RuntimeError):
            wait_until_finished(wrapper, timeout=0.1)
        assert run
        assert wrapper.generator is not None

    def test_circular_strongref_suspended(self):
        run = False

        @send_self
        def func():
            nonlocal run
            this = (yield)()  # NOQA - needed for a circular reference
            run = True
            yield
            run = False

        gc.collect()  # Collect before our own circular reference is created
        wrapper = func().with_weak_ref()
        assert run
        assert wrapper.generator is not None

        after_collected = gc.collect(0)
        assert after_collected == 5  # TODO remove exact check
        assert wrapper.generator is None
