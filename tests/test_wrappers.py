import time
import weakref

from ..send_self import send_self, StrongGeneratorWrapper, WeakGeneratorWrapper

from . import defer


class TestGeneratorWrappers(object):

    def test_constructors(self):
        def func():
            yield
        generator = func()
        refs = [StrongGeneratorWrapper(generator),
                WeakGeneratorWrapper(weakref.ref(generator))]

        for ref in refs:
            assert type(ref.weak_generator) is weakref.ref
            assert ref.weak_generator() is generator
            assert ref.catch_stopiteration is True
            assert ref.debug is False

    def test_equal(self):
        def func():
            yield
        generator = func()
        assert (StrongGeneratorWrapper(generator)
                == StrongGeneratorWrapper(generator))
        assert (WeakGeneratorWrapper(weakref.ref(generator))
                == WeakGeneratorWrapper(weakref.ref(generator)))

    # Also checks preservance of weak_generator object
    def test_with_weak_ref(self):
        run = False

        # Note that `weakref.ref(obj) is weakref.ref(obj)`
        # always holds true,
        # unless you specify a callback parameter
        # for either of the constructors.
        # However, even then they compare equal.
        @send_self(finalize_callback=print)
        def func():
            nonlocal run
            this = yield
            thises = [
                this,
                this.with_weak_ref(),
                this.with_strong_ref().with_weak_ref(),
                this.with_strong_ref().with_strong_ref().with_weak_ref(),
                this()()
            ]
            comp_ref = WeakGeneratorWrapper(weakref.ref(this.generator))
            for i, that in enumerate(thises):
                assert type(that) is WeakGeneratorWrapper, i
                assert that == this

                assert that.weak_generator is this.weak_generator
                assert comp_ref.weak_generator is not that.weak_generator
                assert comp_ref.weak_generator == that.weak_generator
            run = True

        func()
        assert run

    def test_with_strong_ref(self):
        run = False

        # See test_with_weak_ref
        @send_self(finalize_callback=print)
        def func():
            nonlocal run
            this = yield
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
            run = True

        func()
        assert run

    def test_has_terminated(self):
        run = False

        @send_self
        def func():
            nonlocal run
            yield
            run = True

        assert func().has_terminated()
        assert run
        run = False

        def cb(this):
            print('cb run')
            assert not this.has_terminated()
            this.send_wait(True)

        @send_self(debug=True)
        def func2():
            nonlocal run
            this = yield
            assert not this.has_terminated()

            run = yield defer(cb, this, sleep=0)
            yield

        ref = func2()
        time.sleep(0.1)
        assert run

        import inspect
        print(inspect.getgeneratorstate(ref.generator))
        print(ref, ref.generator, ref.generator.gi_frame, ref.has_terminated())
        assert not ref.has_terminated()
        ref.next()
        assert ref.has_terminated()
