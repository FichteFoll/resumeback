# Based on https://gist.github.com/Varriount/aba020b9d43c13d2794b

import weakref
from functools import wraps, partial

import sys
import time
import threading

import sublime_plugin
import sublime


class WeakGeneratorWrapper(object):

    """Wraps a weak reference to a generator and adds convenience features.

    Generally behaves like a normal generator
    in terms of the four methods
    'send', 'throw', 'close' and 'next'/'__next__',
    but has the following convenience features:

    1. Method access will create a strong reference
       to the generator so that you can
       pass them as callback arguments
       from within the generator
       without causing it to get garbage-collected.
       Usually the reference count decreases (possibly to 0)
       when the generator pauses.

    2. The `send` method has a default value
       for its `value` parameter.
       This allows it to be used without a parameter
       when it will behave like `next(generator)`,
       unlike the default implementation of send.

    3. The methods :meth:`send` and :meth:`throw`
       optionally catch ``StopIteration`` exceptions
       so that they are not propagated to the caller
       when the generator terminates.

    4. :meth:`with_strong_ref` (= ``__call__``) will return a wrapper
       with a strong reference to the generator.
       This allows you to pass
       the entire wrapper by itself as a "callback"
       and the delegated function may choose
       between normally sending a value
       or throwing an exception
       where the generator was paused.
    """

    def __init__(self, weak_generator, catch_stopiteration=True, debug=False):
        """__init__

        :type weak_generator: weakref.ref
        :param weak_generator: Weak reference to a generator.

        :type catch_stopiteration: bool
        :param catch_stopiteration:
            Set to `False`
            to not catch StopIteration exceptions
            raised by methods that communicate with a generate,
            i.e. next, __next__, send and throw.

        :type debug: bool
        :param debug:
            Set to `True`
            to get some debug information in `sys.stdout`.
        """
        self.weak_generator = weak_generator
        self.catch_stopiteration = catch_stopiteration
        self.debug = debug

        self._args = (weak_generator, catch_stopiteration, debug)

        if self.debug:
            print("new Wrapper created", self)

    def __del__(self):
        if self.debug:
            print("Wrapper is being deleted", self)

    @property
    def generator(self):
        """The actual generator object, weak-reference unmasked."""
        return self.weak_generator()

    def with_strong_ref(self):
        """Get a StrongGeneratorWrapper with the same settings."""
        return StrongGeneratorWrapper(self.generator, *self._args)

    def with_weak_ref(self):
        """Get a WeakGeneratorWrapper with the same settings."""
        return self

    @property
    def next(self):
        """TODOC"""
        return partial(self._next, self.generator)

    __next__ = next  # Python 3

    def _next(self, generator):
        return self._send(generator)

    @property
    def send(self):
        """TODOC"""
        return partial(self._send, self.generator)

    # TODO Methods that wait until generator is suspended.
    # Check if generator.gi_running works as expected and if it exists
    # in Py2, or catch `ValueError: generator already executing`.

    # A wrapper around send with a default value
    def _send(self, generator, value=None):
        if self.debug:
            print("send:", generator, value)
        if self.catch_stopiteration:
            try:
                return generator.send(value)
            except StopIteration as si:
                print(si)
                return getattr(si, 'value', None)
        else:
            generator.send(value)

    @property
    def throw(self):
        """TODOC"""
        return partial(self._throw, self.generator)

    def _throw(self, generator, *args, **kwargs):
        if self.debug:
            print("throw:", generator, args, kwargs)
        if self.catch_stopiteration:
            try:
                return generator.throw(*args, **kwargs)
            except StopIteration as si:
                return getattr(si, 'value', None)
        else:
            generator.throw(*args, **kwargs)

    @property
    def close(self):
        """Equivalent to `self.generator.close`."""
        return self.generator.close

    __call__ = with_strong_ref


class StrongGeneratorWrapper(WeakGeneratorWrapper):

    """Wraps a generator and adds convenience features.

    Generally operates similar to :class:`WeakGeneratorWrapper`,
    except that it holds a string reference to the generator.
    You will want to pass an instance of this class around
    while the generator is paused
    so that it is not garbage-collected.

    IMPORTANT:
    DO NOT BIND AN INSTANCE OF THIS
    IN THE GENERATOR'S LOCAL SCOPE ITSELF
    (unless you know what you are doing).
    Otherwise the generator will not be garbage-collected
    if it is paused due to a yield
    and not called again.
    """

    generator = None  # Override property of WeakGeneratorWrapper

    def __init__(self, generator, weak_generator=None, *args, **kwargs):
        """__init__

        :type generator: generator
        :param generator: The generator object.

        :type weak_generator: weakref.ref
        :param weak_generator: Weak reference to a generator. Optional.

        For other parameters see :meth:`WeakGeneratorWrapper.__init__`.
        """
        # It's important that the weak_generator object reference is preserved
        # because it will hold the `finalize_callback` callback from @send_self.
        self.generator = generator

        if weak_generator is None:
            weak_generator = weakref.ref(generator)
        super(StrongGeneratorWrapper, self).__init__(weak_generator, *args,
                                                     **kwargs)

    def with_strong_ref(self):
        """Get a StrongGeneratorWrapper with the same settings."""
        return self

    def with_weak_ref(self):
        """Get a WeakGeneratorWrapper with the same settings."""
        return WeakGeneratorWrapper(*self._args)

    __call__ = with_strong_ref


def send_self(catch_stopiteration=True, finalize_callback=None, debug=False):
    """Decorator that sends a generator a wrapper of itself.

    Can be called with parameters or used as a decorator directly.

    When a generator decorated by this is called,
    it gets sent a wrapper of itself
    via the first 'yield' used.
    The wrapper is an instance of :class:`WeakGeneratorWrapper`.
    The function then returns the first yielded value
    while the generator runs as a co-routine.

    Useful for creating generators
    that can leverage callback-based functions
    in a linear style,
    by passing the wrapper or one of its method properties
    as callback parameters
    and then pausing itself with 'yield'.

    IMPORTANT:
    DO NOT BIND STRONG REFERENCES TO THE GENERATOR
    IN THE GENERATOR'S LOCAL SCOPE ITSELF
    (unless you know what you are doing).
    Otherwise the generator will not be garbage-collected
    if it is paused due to a yield
    and not called again.

    See :class:`WeakGeneratorWrapper` for what you can do with it.

    :type catch_stopiteration: bool
    :param catch_stopiteration:
        The wrapper catches ``StopIteration`` exceptions by default.
        If you wish to have them propagated,
        set this to ``False``.
        Forwarded to the Wrapper.

    :type finalize_callback: callable
    :param finalize_callback:
        When the generator is garabage-collected and finalized,
        this callback will be called.
        It will recieve the weak-referenced object
        to the dead referent as first parameter,
        as specified by `weakref.ref`.

    :type debug: bool
    :param debug:
        Set this to ``True``
        if you wish to have some debug output
        printed to sys.stdout.
        Probably useful if you are debugging problems
        with the generator not being resumed or finalized.
        Forwarded to the Wrapper.

    :return:
        The first yielded value of the generator.
    """
    # "catch_stopiteration" needs to be the name of the first parameter. For
    # clarity, we mirror that to first_param and override catch_stopiteration
    # later.
    first_param = catch_stopiteration
    catch_stopiteration = True

    # We either directly call this, or return it to be called by Python's
    # decorator mechanism.
    def _send_self(func):
        @wraps(func)
        def send_self_wrapper(*args, **kwargs):
            # optional but for clarity
            nonlocal catch_stopiteration, finalize_callback, debug

            # Create generator
            generator = func(*args, **kwargs)

            # Register finalize_callback to be called when the object is gc'ed
            weak_generator = weakref.ref(generator, finalize_callback)

            # The first yielded value will be used as return value of the
            # "initial call to the generator" (=> this wrapper).
            ret_value = next(generator)  # Start generator

            # Send wrapper to the generator
            gen_wrapper = WeakGeneratorWrapper(
                weak_generator,
                catch_stopiteration,
                debug
            )
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
        catch_stopiteration = first_param
        return _send_self


################################################################################
################################################################################
################################################################################


# Set to true for very detailed debug printing (forwarded to @send_self
# decorator).
DEBUG = True


# Following are a few funtions that are utilized to:
# 1. Print detailed debug information about the objects used and their
#    references.
# 2. Show case a few uses of generators as co-routines, such as throwing an
#    exception.

def monitor_refcounts(ref):
    oldweak, oldstrong = 0, 0
    print("start minitoring with", ref)
    while True:
        time.sleep(0.05)

        obj = ref()
        if not obj:
            break
        newweak, newstrong = weakref.getweakrefcount(ref), sys.getrefcount(obj)
        del obj

        msg = ("weak refcount: %d - strong refcount: %d"
               % (newweak, newstrong))

        if (newweak, newstrong) != (oldweak, oldstrong):
            oldweak, oldstrong = newweak, newstrong
            print(msg)

    print("Object was garbage collected", ref)


def defer(callback, call=True):

    def func():
        time.sleep(0.4)
        if call:
            callback()
        else:
            print("generator is not re-called")

    threading.Thread(target=func).start()


def test_throw(gw, i):

    def func():
        time.sleep(0.4)
        if i >= 3:
            ret = gw.throw(TypeError, "%d is greater than 2" % i)
            print("catched and returned:", ret)  # should be the above message
            next(gw)  # resume
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
        print("We passed 300, but", e)
        yield "yeah, that was unreasonable"


def the_last_yield(cb):
    def func():
        time.sleep(0.2)
        val = cb(10)
        print("returned value", val)

    threading.Thread(target=func).start()


class TestCommandCommand(sublime_plugin.WindowCommand):

    def wont_be_finished(self):
        this = yield
        if this.debug:
            threading.Thread(target=monitor_refcounts,
                             args=[this.weak_generator]).start()

        print("wont_be_finished")
        # this is where the initial caller will be resumed
        yield defer(this.send)
        print("middle~")
        yield defer(this.send, False)
        print("this should not be printed")

    @send_self(finalize_callback=lambda x: print("generator finalized"),
               debug=DEBUG)
    def run(self):
        this = yield
        if this.debug:
            threading.Thread(target=monitor_refcounts,
                             args=[this.weak_generator]).start()

        print("original weak-ref variant:", this)
        this = this()
        print("strong-ref variant:", this)
        this = this.with_weak_ref()
        print("new weak-ref variant:", this)

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
        # can have data sent to itself (even exceptions).
        # Only for Python 3.3! (new syntax)
        yield from sub_generator(this)

        # Different method to invoke a sub-generator (and less effective)
        wont_be_finished = send_self(
            finalize_callback=this.send,
            debug=this.debug
        )(self.wont_be_finished)

        print("launching weird sub-generator")
        old_obj = yield wont_be_finished()
        print("weakref of other sub-generator:", old_obj)

        # This creates a strong reference and causes cyclic reference.
        # DON'T TRY THIS AT HOME! MEMORY LEAK!
        # this = this()
        # yield

        x = yield the_last_yield(this.send)

        # return a value (will be the_last_yield's return
        # value of calling `this.send`).
        # This is a Python 3.3 feature.
        return x * 12


class Test2CommandCommand(sublime_plugin.WindowCommand):
    # This is a sub-generator
    def prompt(self, this, caption):
        return (yield self.window.show_input_panel(caption, '', this.send,
                                                   None, None))

    @send_self(finalize_callback=lambda x: print("finalized"))
    def run(self):
        this = yield  # This should be the first line

        text = yield self.window.show_input_panel("Enter something", '',
                                                  this.send, None, None)
        print("Entered the following text:", text)

        more_text = [(yield from self.prompt(this,
                                             "Please enter some more text " + i)
                      ) for i in range(4)]

        selection = yield self.window.show_quick_panel(more_text, this.send)
        if selection == -1:
            print("No selection made")
        else:
            print("Selected:", more_text[selection])
