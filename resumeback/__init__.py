"""Library for using callbacks to resume your code."""

from collections.abc import Callable
from functools import partial, update_wrapper
import inspect
import threading
import time
import weakref


__version__ = "0.2.0dev0"

version_info = __version__.split('.')

__author__ = "FichteFoll <fichtefoll2@googlemail.com>"

__all__ = (
    'send_self',
    'send_self_return',
    'WeakGeneratorWrapper',
    'StrongGeneratorWrapper',
    'WaitTimeoutError',
)


class WaitTimeoutError(RuntimeError):
    """Error class that is raised when a specified timeout is exceeded."""
    pass


class WeakGeneratorWrapper(object):

    """Wraps a weak reference to a generator and adds convenience features."""

    def __init__(self, weak_generator, catch_stopiteration=True, debug=False):
        self.weak_generator = weak_generator
        self.catch_stopiteration = catch_stopiteration
        self.debug = debug

        self._args = (weak_generator, catch_stopiteration, debug)

        # We use this lock
        # so that the '*_wait' methods do not get screwed
        # after checking `generator.gi_running`
        # and WILL succeed,
        # as long as the wrapper is used.
        # This is of course bypassed
        # by somone calling the generator's methods directly.
        self._lock = threading.RLock()

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
        """Get a StrongGeneratorWrapper with the same attributes."""
        return StrongGeneratorWrapper(self.generator, *self._args)

    def with_weak_ref(self):
        """Get a WeakGeneratorWrapper with the same attributes."""
        return self

    # Utility and shorthand functions/methods
    # for generating our "property" methods.
    def _wait(self, generator, method, timeout=None, *args, **kwargs):
        """Wait until generator is paused before running 'method'."""
        if self.debug:
            print("waiting for %s to pause" % generator)

        original_timeout = timeout
        while timeout is None or timeout > 0:
            last_time = time.time()
            if self._lock.acquire(False):  # timeout param was added in 3.2
                try:
                    if self.can_resume():
                        return method(generator, *args, **kwargs)
                    elif self.has_terminated():
                        raise RuntimeError("%s has already terminated" % generator)
                finally:
                    self._lock.release()

            if timeout is not None:
                timeout -= time.time() - last_time

        msg = "%s did not pause after %ss" % (generator, original_timeout)
        if self.debug:
            print(msg)
        raise WaitTimeoutError(msg)

    # The "properties"
    @property
    def next(self):
        """Resume the generator."""
        return partial(self._next, self.generator)

    __next__ = next  # Python 3

    def _next(self, generator):
        if self.debug:
            print("next:", generator)
        return self._send(generator)

    @property
    def next_wait(self):
        """Wait before nexting a value to the generator to resume it."""
        return partial(self._next_wait, self.generator)

    def _next_wait(self, generator, timeout=None):
        return self._wait(generator, self._next, timeout)

    @property
    def next_wait_async(self):
        """Create a waiting daemon thread to resume the generator."""
        return partial(self._next_wait_async, self.generator)

    def _next_wait_async(self, generator, timeout=None):
        thread = threading.Thread(
            target=self._next_wait,
            args=(generator, timeout)
        )
        thread.daemon = True
        if self.debug:
            print("spawned new thread to call %s_wait: %r" % ('next', thread))
        thread.start()
        return thread

    @property
    def send(self):
        """Send a value to the generator to resume it."""
        return partial(self._send, self.generator)

    # A wrapper around send with a default value
    def _send(self, generator, value=None):
        if self.debug:
            print("send:", generator, value)
        with self._lock:
            if self.catch_stopiteration:
                try:
                    return generator.send(value)
                except StopIteration as si:
                    return getattr(si, 'value', None)
            else:
                return generator.send(value)

    @property
    def send_wait(self):
        """Wait before sending a value to the generator to resume it."""
        return partial(self._send_wait, self.generator)

    def _send_wait(self, generator, value=None, timeout=None):
        return self._wait(generator, self._send, timeout, value)

    @property
    def send_wait_async(self):
        """Create a waiting daemon thread to send a value to the generator."""
        return partial(self._send_wait_async, self.generator)

    def _send_wait_async(self, generator, value=None, timeout=None):
        thread = threading.Thread(
            target=self._send_wait,
            args=(generator,),
            kwargs={'value': value, 'timeout': timeout}
        )
        thread.daemon = True
        if self.debug:
            print("spawned new thread to call %s_wait: %r" % ('send', thread))
        thread.start()
        return thread

    @property
    def throw(self):
        """Raises an exception where the generator was suspended."""
        return partial(self._throw, self.generator)

    def _throw(self, generator, *args, **kwargs):
        if self.debug:
            print("throw:", generator, args, kwargs)
        with self._lock:
            if self.catch_stopiteration:
                try:
                    return generator.throw(*args, **kwargs)
                except StopIteration as si:
                    return getattr(si, 'value', None)
            else:
                return generator.throw(*args, **kwargs)

    @property
    def throw_wait(self):
        """Wait before throwing a value to the generator to resume it."""
        return partial(self._throw_wait, self.generator)

    def _throw_wait(self, generator, *args, **kwargs):
        timeout = kwargs.pop('timeout', None)
        return self._wait(generator, self._throw, timeout, *args, **kwargs)

    @property
    def throw_wait_async(self):
        """Create a waiting daemon thread to throw a value in the generator."""
        return partial(self._throw_wait_async, self.generator)

    def _throw_wait_async(self, *args, **kwargs):
        thread = threading.Thread(
            target=self._throw_wait,
            args=args,
            kwargs=kwargs
        )
        thread.daemon = True
        if self.debug:
            print("spawned new thread to call %s_wait: %r" % ('throw', thread))
        thread.start()
        return thread

    @property
    def close(self):
        """Equivalent to ``self.generator.close``."""
        return self.generator.close

    def has_terminated(self):
        """Check if the wrapped generator has terminated."""
        # TOCHECK relies on generator.gi_frame
        # Equivalent to
        # `inspect.getgeneratorstate(self.generator) == inspect.GEN_CLOSED`
        gen = self.generator
        return gen is None or gen.gi_frame is None

    def can_resume(self):
        """Test if the generator can be resumed, i.e. is not running or closed."""
        # TOCHECK relies on generator.gi_frame
        # Equivalent to `inspect.getgeneratorstate(self.generator) in
        # (inspect.GEN_CREATED, inspect.GEN_SUSPENDED)`,
        # which is only available starting 3.2.
        gen = self.generator
        return (gen is not None
                and not gen.gi_running
                and gen.gi_frame is not None)

    def __eq__(self, other):
        if type(other) is WeakGeneratorWrapper:
            return self._args == other._args
        return NotImplemented

    __call__ = with_strong_ref


class StrongGeneratorWrapper(WeakGeneratorWrapper):

    """Wraps a generator and adds convenience features."""

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
        # because it will hold `finalize_callback` from @send_self.
        self.generator = generator

        if weak_generator is None:
            weak_generator = weakref.ref(generator)

        super(StrongGeneratorWrapper, self).__init__(weak_generator, *args,
                                                     **kwargs)

    def with_strong_ref(self):
        """Get a StrongGeneratorWrapper with the same attributes."""
        return self

    def with_weak_ref(self):
        """Get a WeakGeneratorWrapper with the same attributes."""
        return WeakGeneratorWrapper(*self._args)

    def __eq__(self, other):
        if type(other) is StrongGeneratorWrapper:
            return (self.generator == other.generator
                    and self._args == other._args)
        return NotImplemented

    __call__ = with_weak_ref


class send_self:  # noqa: N801

    """Decorator that sends a generator a wrapper of itself.

    Can be called with parameters or used as a decorator directly.
    """

    def __init__(self, func=None, *, catch_stopiteration=True, finalize_callback=None, debug=False):
        # Typechecking
        type_table = [
            ('catch_stopiteration', bool),
            ('debug', bool),
            ('finalize_callback', (Callable, type(None)))
        ]
        if func is not None and not inspect.isgeneratorfunction(func):
            raise TypeError("Callable must be a generatorfunction")

        for name, type_ in type_table:
            val = locals()[name]
            if not isinstance(val, type_):
                raise TypeError("Expected %s for parameter '%s', got %s"
                                % (type_, name, type(val)))

        self.catch_stopiteration = catch_stopiteration
        self.finalize_callback = finalize_callback
        self.debug = debug
        self.func = func

        # Wrap func if it was specified
        if func:
            update_wrapper(self, func)

    def _start_generator(self, generator):
        # Start generator
        next(generator)

        # Register finalize_callback to be called when the object is gc'ed
        weak_generator = weakref.ref(generator, self.finalize_callback)

        # Build wrapper and send to the generator
        gen_wrapper = StrongGeneratorWrapper(
            generator,
            weak_generator,
            self.catch_stopiteration,
            self.debug
        )
        gen_wrapper.send(gen_wrapper.with_weak_ref())
        return gen_wrapper

    def __call__(self, *args, **kwargs):
        # Second part of decorator usage, i.e. `@send_self(True) \n def ...`
        if not self.func:
            if not args or not callable(args[0]):
                raise RuntimeError("send_self wrapper has not properly been initialized yet")
            else:
                if not inspect.isgeneratorfunction(args[0]):
                    raise ValueError("Callable must be a generatorfunction")
                self.func = args[0]
                update_wrapper(self, self.func)
                return self

        # Create generator
        generator = self.func(*args, **kwargs)

        return self._start_generator(generator)


class send_self_return(send_self):  # noqa: N801

    """Decorator that sends a generator a wrapper of itself."""

    def _start_generator(self, generator):
        # The first yielded value will be used as return value of the
        # "initial call to the generator" (=> this wrapper)
        ret_value = next(generator)

        # Register finalize_callback to be called when the object is gc'ed
        weak_generator = weakref.ref(generator, self.finalize_callback)

        # Build wrapper and send to the generator
        weak_gen_wrapper = WeakGeneratorWrapper(
            weak_generator,
            self.catch_stopiteration,
            self.debug
        )
        weak_gen_wrapper.send(weak_gen_wrapper)
        return ret_value
