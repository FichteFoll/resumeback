from __future__ import print_function

from functools import partial, wraps
import inspect
import threading
import time
import weakref


__all__ = (
    'StrongGeneratorWrapper',
    'WaitTimeoutError',
    'WeakGeneratorWrapper',
    'send_self',
    'send_self_return',
)


class WaitTimeoutError(RuntimeError):
    pass


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

    .. attribute:: generator
        Strong reference to the generator.
        Will be retrieved from the :attr:`weak_geenrator` in a property.

    .. attribute:: weak_generator
        Instance of ``weakref.ref``
        and weak reference to the generator

    .. attribute:: catch_stopiteration
        If ``True``,
        ``StopIteration`` exceptions raised by the generator
        will be caught by the 'next', '__next__', 'send' and 'throw' methods.
        On Python >3.3 its value will be returned if available,
        ``None`` otherwise.

    .. attribute:: debug
        If ``True``,
        some debug information will be printed to ``sys.stdout``.
    """

    def __init__(self, weak_generator, catch_stopiteration=True, debug=False):
        """__init__

        :type weak_generator: weakref.ref
        :param weak_generator: Weak reference to a generator.

        :type catch_stopiteration: bool
        :param catch_stopiteration:
            Whether ``StopIteration`` exceptions should be caught.
            Default: ``True``

        :type debug: bool
        :param debug:
            Whether debug information should be printed.
            Default: ``False``
        """
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
            if self._lock.acquire(timeout=timeout or -1):
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
        """Resume the generator.

        Depending on :attr:`cls.catch_stopiteration`,
        ``StopIteration`` exceptions will be caught
        and their values returned instead,
        if any.

        :return:
            The next yielded value
            or the value that the generator returned
            (using ``StopIteration`` or returning normally,
            Python>3.3).

        :raises:
            Any exception raised by the generator.
        """
        return partial(self._next, self.generator)

    __next__ = next  # Python 3

    def _next(self, generator):
        if self.debug:
            print("next:", generator)
        return self._send(generator)

    @property
    def next_wait(self):
        """Wait before nexting a value to the generator to resume it.

        Generally works like :meth:`next`,
        but will wait until a thread is paused
        before attempting to resume it.

        *Additional* information:

        :type timeout float:
        :param timeout:
            Time in seconds that should be waited
            for suspension of the generator.
            No timeout will be in effect
            if ``None``.

        :raises WaitTimeoutError:
            if the generator has not been paused.
        :raises RuntimeError:
            if the generator has already terminated.
        """
        return partial(self._next_wait, self.generator)

    def _next_wait(self, generator, timeout=None):
        return self._wait(generator, self._next, timeout)

    @property
    def next_wait_async(self):
        """Create a waiting daemon thread to resume the generator.

        Works like :meth:`next_wait`
        but does it asynchronously.
        The thread spawned raises :cls:`WaitTimeoutError`
        when it times out.

        :rtype threading.Thread:
        :return:
            The created and running thread.
        """
        return partial(self._next_wait_async, self.generator)

    def _next_wait_async(self, generator, timeout=None):
        thread = threading.Thread(
            target=self._next_wait,
            args=(generator, timeout),
            daemon=True
        )
        if self.debug:
            print("spawned new thread to call %s_wait: %r" % ('next', thread))
        thread.start()
        return thread

    @property
    def send(self):
        """Send a value to the generator to resume it.

        Depending on :attr:`cls.catch_stopiteration`,
        ``StopIteration`` exceptions will be caught
        and their values returned instead,
        if any.

        :param value:
            The value to send to the generator.
            Default is ``None``,
            which results in the same behavior
            as calling 'next'/'__next__'.

        :return:
            The next yielded value
            or the value that the generator returned
            (using ``StopIteration`` or returning normally,
            Python>3.3).

        :raises:
            Any exception raised by the generator.
        """
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
        """Wait before sending a value to the generator to resume it.

        Generally works like :meth:`send`,
        but will wait until a thread is paused
        before attempting to resume it.

        *Additional* information:

        :type timeout float:
        :param timeout:
            Time in seconds that should be waited
            for suspension of the generator.
            No timeout will be in effect
            if ``None``.

        :raises WaitTimeoutError:
            if the generator has not been paused.
        :raises RuntimeError:
            if the generator has already terminated.
        """
        return partial(self._send_wait, self.generator)

    def _send_wait(self, generator, value=None, timeout=None):
        return self._wait(generator, self._send, timeout, value)

    @property
    def send_wait_async(self):
        """Create a waiting daemon thread to send a value to the generator.

        Works like :meth:`send_wait`
        but does it asynchronously.
        The thread spawned raises :cls:`WaitTimeoutError`
        when it times out.

        :rtype threading.Thread:
        :return:
            The created and running thread.
        """
        return partial(self._send_wait_async, self.generator)

    def _send_wait_async(self, generator, value=None, timeout=None):
        thread = threading.Thread(
            target=self._send_wait,
            args=(generator,),
            kwargs={'value': value, 'timeout': timeout},
            daemon=True
        )
        if self.debug:
            print("spawned new thread to call %s_wait: %r" % ('send', thread))
        thread.start()
        return thread

    @property
    def throw(self):
        """Raises an exception where the generator was suspended.

        Depending on :attr:`cls.catch_stopiteration`,
        ``StopIteration`` exceptions will be caught
        and their values returned instead,
        if any.

        Accepts and expects the same parameters as ``generator.throw``.

        :param type:
        :param value:
        :param traceback:
            Refer to the standard Python documentation.

        :return:
            The next yielded value
            or the value that the generator returned
            (using ``StopIteration`` or returning normally,
            Python>3.3).

        :raises:
            Any exception raised by the generator.
            This includes the thrown exception
            if the generator does not catch it
            and excludes `StopIteration`
            if :attr:`catch_stopiteration` is set.
        """
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
        """Wait before throwing a value to the generator to resume it.

        Works like :meth:`throw`,
        but will wait until a thread is paused
        before attempting to resume it.

        *Additional* information:

        :type timeout float:
        :param timeout:
            Time in seconds that should be waited
            for suspension of the generator.
            No timeout will be in effect
            if ``None``.

        :raises WaitTimeoutError:
            if the generator has not been paused.
        :raises RuntimeError:
            if the generator has already terminated.
        """
        return partial(self._throw_wait, self.generator)

    def _throw_wait(self, generator, *args, **kwargs):
        timeout = kwargs.pop('timeout', None)
        return self._wait(generator, self._throw, timeout, *args, **kwargs)

    @property
    def throw_wait_async(self):
        """Create a waiting daemon thread to throw a value in the generator.

        Works like :meth:`throw_wait`
        but does it asynchronously.
        The thread spawned raises :cls:`WaitTimeoutError`
        when it times out.

        :rtype threading.Thread:
        :return:
            The created and running thread.
        """
        return partial(self._throw_wait_async, self.generator)

    def _throw_wait_async(self, *args, **kwargs):
        thread = threading.Thread(
            target=self._throw_wait,
            args=args,
            kwargs=kwargs,
            daemon=True
        )
        if self.debug:
            print("spawned new thread to call %s_wait: %r" % ('throw', thread))
        thread.start()
        return thread

    @property
    def close(self):
        """Equivalent to ``self.generator.close``."""
        return self.generator.close

    def has_terminated(self):
        """Check if the wrapped generator has terminated.

        :return bool:
            Whether the generator has terminated.
        """
        # Equivalent to
        # `inspect.getgeneratorstate(self.generator) == inspect.GEN_CLOSED`
        gen = self.generator
        return gen is None or gen.gi_frame is None

    def can_resume(self):
        """Test if the generator can be resumed, i.e. is not running or closed.

        :return bool:
            Whether the generator can be resumed.
        """
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

    """Wraps a generator and adds convenience features.

    Operates similar to :class:`WeakGeneratorWrapper`,
    except that it holds a strong reference to the generator.
    Use this class
    if you want to pass the generator wrapper itself around,
    so that the generator is not garbage-collected.

    ``__call__`` is an alias for :meth:`with_weak_ref`.

    IMPORTANT:
    DO NOT BIND AN INSTANCE OF THIS
    IN THE GENERATOR'S LOCAL SCOPE ITSELF
    (unless you know what you are doing).
    Otherwise the generator will not be garbage-collected
    if it is paused due to a yield
    and not resumed again.
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


def send_self(catch_stopiteration=True, finalize_callback=None, debug=False,
              __return_yield=False):
    """Decorator that sends a generator a wrapper of itself.

    Can be called with parameters or used as a decorator directly.

    When a generator decorated by this is called,
    it gets sent a wrapper of itself
    via the first 'yield' used.
    The wrapper is an instance of :class:`WeakGeneratorWrapper`.
    The function then returns said wrapper.

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
    and not called again
    due to a cyclic reference.

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

    :raises TypeError:
        If the parameters are not of types as specified.
    :raises ValueError:
        If the callable is not a generator
        or ``finalize_callback`` is not callable.

    :return:
        A :class:`StrongGeneratorWrapper` instance
        holding the created generator.
    """
    # "catch_stopiteration" needs to be the name of the first parameter. For
    # clarity, we mirror that to first_param and override catch_stopiteration
    # later.
    first_param = catch_stopiteration
    catch_stopiteration = first_param if not callable(first_param) else True

    # Typechecking
    type_table = [
        ('catch_stopiteration', catch_stopiteration, bool),
        ('debug', debug, bool),
    ]
    for name, val, type_ in type_table:
        if not isinstance(val, type_):
            raise TypeError("Expected %s for parameter '%s', got %s"
                            % (type_, name, type(val)))

    if finalize_callback is not None and not callable(finalize_callback):
        raise TypeError("Expected callable type for 'finalize_callback'")

    if callable(first_param):
        # If the argument is a callable, we've been used without being directly
        # passed an argument by the user, and thus should call _send_self directly.
        return _send_self(catch_stopiteration, finalize_callback, debug,
                          __return_yield, first_param)
    else:
        # Someone has called @send_self(...) with parameters and thus we return
        # _send_self to be called indirectly, as a partial.
        return partial(_send_self,
                       catch_stopiteration, finalize_callback, debug,
                       __return_yield)


def send_self_return(catch_stopiteration=True, finalize_callback=None, debug=False):
    """Decorator that sends a generator a wrapper of itself.

    Behaves exactly like :func:`send_self`,
    except that it returns the first yielded value
    of the generator instead of a wrapper.

    :return:
        The first yielded value of the generator.
    """
    return send_self(catch_stopiteration, finalize_callback, debug, __return_yield=True)


# We either directly call this, or return it to be called by Python's
# decorator mechanism.
# Since functools.partial is used, 'func' needs to be at the end.
def _send_self(catch_stopiteration, finalize_callback, debug, return_yield,
               func):
    if not inspect.isgeneratorfunction(func):
        raise ValueError("Callable must be a generatorfunction")

    @wraps(func)
    def send_self_wrapper(*args, **kwargs):
        # optional but for clarity
        nonlocal catch_stopiteration, finalize_callback, return_yield, debug
        nonlocal func

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
        gen_wrapper.send(gen_wrapper)

        if not return_yield:
            ret_value = gen_wrapper.with_strong_ref()
        return ret_value

    return send_self_wrapper
