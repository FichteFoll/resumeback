# Based on https://gist.github.com/Varriount/aba020b9d43c13d2794b

import weakref
from functools import wraps, partial

import sys
import time
import threading

import sublime_plugin
import sublime


class GeneratorWrapper():
    """TODOC

    An instance of this will be sent to the generator function. `send`
    holds a wrapper function that calls either next(gen) or gen.send(val).
    """

    # Save some overhead here. Not exactly needed but you shouldn't mess with
    # instances of this class, only use or call.
    __slots__ = ('generator', 'generator_ref', 'catch_stopiteration')

    def __init__(self, generator, generator_ref, catch_stopiteration=True):
        self.generator = generator
        self.generator_ref = generator_ref
        self.catch_stopiteration = catch_stopiteration

    def __del__(self):
        print("Wrapper is being deleted", self)

    def _get_generator(self):
        return self.generator or self.generator_ref()

    @property
    def send(self):
        return partial(self._send, self._get_generator())

    # a wrapper around send with a default value
    def _send(self, generator, value=None):
        print("send:", generator, value)
        if self.catch_stopiteration:
            try:
                return generator.send(value)
            except StopIteration:
                return None
        else:
            generator.send(value)

    @property
    def throw(self):
        return partial(self._throw, self._get_generator())

    def _throw(self, generator, *args, **kwargs):
        print("throw:", generator, args, kwargs)
        if self.catch_stopiteration:
            try:
                return generator.throw(*args, **kwargs)
            except StopIteration:
                return None
        else:
            generator.throw(*args, **kwargs)

    @property
    def close(self):
        return self._get_generator().close

    def with_strong_ref(self):
        if self.generator:
            return self
        else:
            return self.__class__(self._get_generator(), None,
                                  self.catch_stopiteration)

    __call__ = with_strong_ref


def monitor_refcounts(ref):
    oldweak, oldstrong = 0, 0
    print("start minitoring", ref())
    while True:
        time.sleep(0.05)

        obj = ref()
        if not obj:
            break
        newweak, newstrong = weakref.getweakrefcount(ref), sys.getrefcount(obj)
        del obj

        msg = ("weak refcount: %d - strong refcount: %d"
               % (newweak, newstrong))
        sublime.status_message(msg)

        if (newweak, newstrong) != (oldweak, oldstrong):
            oldweak, oldstrong = newweak, newstrong
            print(msg)

    print("Object was garbage collected")
    sublime.status_message("Object was garbage collected")


def send_self(use_weakref=True, catch_stopiteration=True):
    """Decorator that sends a generator a wrapper of itself.

    The returned function instantiates and sends a generator a wrapper of itself
    via the first 'yield' used. The wrapper is an instance of GeneratorWrapper.

    Useful for creating generators that can leverage callback-based functions in
    a linear style, by passing the wrapper as callback in the first yield
    statement.

    The generator wrapper wraps a weak reference (weakref.ref) by default. To
    override this set use_weakref to `False`, though you potentially need to
    clean up the generator yourself afterwards in case it is not resumed because
    it won't be garbage collected.

    The wrapper catches StopIteration exceptions by default. If you wish to have
    them propagated, set catch_stopiteration to `False`.
    """
    # "use_weakref" needs to be the name of the first parameter. For clarity, we
    # mirror that to first_param and override use_weakref later.
    first_param = use_weakref
    use_weakref = True

    # We either directly call this, or return it to be called by Python's
    # decorator mechanism.
    def _send_self(func):
        @wraps(func)
        def send_self_wrapper(*args, **kwargs):
            nonlocal use_weakref, catch_stopiteration  # optional but for clarity

            # Create generator
            generator = func(*args, **kwargs)

            # "initial call to the generator" (=> this wrapper).
            # The first yielded value will be used as return value of the
            weak_generator = weakref.ref(generator, lambda r: print("finalized"))
            threading.Thread(target=monitor_refcounts,
                             args=[weak_generator]).start()

            ret_value = next(generator)  # Start the generator

            gen_wrapper = GeneratorWrapper(None, weak_generator,
                                           catch_stopiteration)
            # Send generator wrapper to the generator.
            generator.send(gen_wrapper)

            return ret_value

        return send_self_wrapper

    # If the argument is a callable, we've been used without being directly
    # passed an argument by the user, and thus should call _send_self directly.
    if callable(first_param):
        # No arguments, this is the decorator.
        return _send_self(first_param)
    else:
        # Someone has called @send_self(...) with parameters and thus we need to
        # return _send_self to be called indirectly.
        use_weakref = first_param
        return _send_self


def defer(callback, call=True):

    def func():
        time.sleep(0.4)
        if call:
            callback()
        else:
            print("generator will be deleted (if weakref'd)")

    threading.Thread(target=func).start()


def test_throw(gw, i):

    def func():
        time.sleep(0.4)
        if i >= 3:
            ret = gw.throw(TypeError, "%d is greater than 2" % i)
            print("catched and returned:", ret)  # should be the above message
            gw.send()  # resume
        else:
            gw.send(i * 10)

    threading.Thread(target=func).start()


def sub_generator(this):
    print("waiting in sub_generator")
    yield sublime.set_timeout(this.send, 200)
    print("resumed in sub_generator")

    try:
        yield test_throw(this(), 300)
    except TypeError as e:
        print("We wanted to pass 300", e)
        yield "yeah, that was unreasonable"


class TestCommandCommand(sublime_plugin.WindowCommand):
    @send_self
    def run(self):
        this = yield

        yield defer(this.send)
        print("one")
        yield sublime.set_timeout(this.send, 200)
        print("one.one")

        for i in range(5):
            try:
                ret = yield test_throw(this(), i)
            except TypeError as e:
                print("oops!", e)
                yield "sorry"  # we are resumed by the test_throw thread
                break
            else:
                print("result", i, ret)
        print("two")

        # Utilize a sub-generator and pass the wrapper as argument so that it
        # can have data sent to itself.
        yield from sub_generator(this)

        # text = yield self.window.show_input_panel("Enter stuff", '', this.send,
        #                                           None, None)
        # print(text)
        yield defer(this.send, False)
        print("this should not be printed")
