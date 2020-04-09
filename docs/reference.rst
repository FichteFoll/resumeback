===========
 Reference
===========

.. currentmodule:: resumeback


.. contents::


``resume_back`` module
======================

.. attribute:: __version__

   The version of the module as a string,
   following the semver__ 2.0.0 spec.

   __ http://semver.org


``@send_self`` decorator
========================


.. decorator:: send_self
.. decorator:: send_self(*, catch_stopiteration=True, finalize_callback=None, debug=False)

   Decorator that sends a "generator function" a wrapper of its instance.

   Can be called with parameters or used as a decorator directly.

   When a generator decorated by this is called,
   it receives a wrapper of its instance as the first parameter.
   The wrapper is an instance of :class:`WeakGeneratorWrapper`.
   The function then returns said wrapper.

   Useful for creating generators
   that can leverage callback-based functions
   in a linear style,
   by passing the wrapper or one of its method properties
   as callback parameters
   and then pausing itself with ``yield``.

   For usage with :func:`classmethod` or :func:`staticmethod`,
   use :func:`~resumeback.send_self` first and wrap it with the
   ``*method`` decorator.

   All provided arguments are stored as attributes
   and may be modified before called.

   .. note::

      Binding a strong reference to the generator
      in the generator's scope itself
      will create a circular reference.

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
      A :class:`StrongGeneratorWrapper` instance
      holding the created generator.

   :raises TypeError:
      If the parameters are not of types as specified.
   :raises ValueError:
      If the callable is not a generator function.


   .. attribute:: func

      The wrapped generator function.


Wrappers
========

.. class:: WeakGeneratorWrapper(weak_generator, catch_stopiteration=True, debug=False)

   Wraps a weak reference to a generator and adds convenience features.

   Generally behaves like a normal generator
   in terms of the four methods
   :meth:`send`, :meth:`throw`, :meth:`close` and :meth:`next`
   (or with the global ``next`` funtion),
   but has the following convenience features:

   1. Method access will create a strong reference
      to the generator so that you can
      pass them as callback arguments
      from within the generator
      without causing it to get garbage-collected.
      Usually the reference count decreases (possibly to 0)
      when the generator pauses.

   2. The :meth:`send` method has a default value
      for its ``value`` parameter.
      This allows it to be used without a parameter,
      where it will behave like `next(generator)`,
      unlike the default implementation of send.

   3. The methods :meth:`send` and :meth:`throw`
      optionally catch ``StopIteration`` exceptions
      so that they are not propagated to the caller
      when the generator terminates.

   4. :meth:`with_strong_ref` (= :meth:`__call__`)
      will return a wrapper
      with a strong reference to the generator.
      This allows you to pass
      the entire wrapper by itself as a "callback"
      and the delegated function may choose
      between normally sending a value
      or throwing an exception
      where the generator was paused.

   :type weak_generator: weakref.ref
   :param weak_generator: Weak reference to a generator.

   :type catch_stopiteration: bool
   :param catch_stopiteration:
      If ``True``,
      ``StopIteration`` exceptions raised by the generator
      will be caught by the 'next', '__next__', 'send' and 'throw' methods.
      On Python >3.3 its value will be returned if available,
      ``None`` otherwise.

   :type debug: bool
   :param debug:
      Whether debug information should be printed.


   .. attribute:: generator

      Strong reference to the generator.
      Will be retrieved from :attr:`weak_generator` in a property.

   .. attribute:: weak_generator

      Instance of ``weakref.ref``
      and weak reference to the generator

   .. attribute:: catch_stopiteration

   .. attribute:: debug


   .. method:: next()

      Resume the generator.

      Depending on :attr:`catch_stopiteration`,
      ``StopIteration`` exceptions will be caught
      and their values returned instead,
      if any.

      :return:
          The next yielded value
          or the value that the generator returned
          (using ``StopIteration`` or returning normally,
          Python>3.3).

      :raises:
          Any exception raised by ``generator.next`` (or the generator).


   .. method:: with_strong_ref()

      Get a :class:`StrongGeneratorWrapper` with the same attributes.

   .. method:: with_weak_ref()

      Get a :class:`WeakGeneratorWrapper` with the same attributes.

   .. method:: next_wait(timeout=None)

      Wait before nexting a value to the generator to resume it.

      Generally works like :meth:`next`,
      but will wait until a thread is paused
      before attempting to resume it.

      *Additional* information:

      :type timeout float:
      :param timeout:
         Time in seconds that should be waited
         for suspension of the generator.
         No timeout will be in effect
         for ``None``.

      :raises WaitTimeoutError:
         if the generator has not paused in time.
      :raises RuntimeError:
         if the generator has already terminated.

   .. method:: next_wait_async(timeout=None)

      Create a waiting daemon thread to resume the generator.

      Works like :meth:`next_wait`
      but does so asynchronously.
      The spawned thread raises :exc:`WaitTimeoutError`
      when it times out.

      :rtype: threading.Thread
      :return:
         The created and running thread.

   .. method:: send(value)

      Send a value to the generator to resume it.

      Depending on :attr:`catch_stopiteration`,
      ``StopIteration`` exceptions will be caught
      and their values returned instead,
      if any.

      :param value:
         The value to send to the generator.
         Default is ``None``,
         which results in the same behavior
         as calling :meth:`next`
         or using the global 'next' function.

      :return:
         The next yielded value
         or the value that the generator returned
         (using ``StopIteration`` or returning normally,
         Python>3.3).

      :raises:
         Any exception raised by ``generator.send``.

   .. method:: send_wait(value, timeout=None)

      Wait before sending a value to the generator to resume it.

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

   .. method:: send_wait_async(value, timeout=None)

      Create a waiting daemon thread to send a value to the generator.

      Works like :meth:`send_wait`
      but does so asynchronously.
      The spawned thread raises :exc:`WaitTimeoutError`
      when it times out.

      :rtype: threading.Thread
      :return:
         The created and running thread.

   .. method:: throw(type[, value[, traceback]])

      Raises an exception where the generator was suspended.

      Depending on :attr:`catch_stopiteration`,
      ``StopIteration`` exceptions will be caught
      and their values returned instead,
      if any.

      Accepts and expects the same parameters as ``generator.throw``.

      :return:
         The next yielded value
         or the value that the generator returned
         (using ``StopIteration`` or returning normally,
         Python>3.3).

      :raises:
         Any exception raised by the generator.
         This includes the thrown exception
         if the generator does not catch it
         and excludes `StopIteration`,
         if :attr:`catch_stopiteration` is set.

   .. method:: throw_wait(type[, value[, traceback]], timeout=None)

      Wait before throwing a value to the generator to resume it.

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

   .. method:: throw_wait_async(type[, value[, traceback]], timeout=None)

      Create a waiting daemon thread to throw a value to the generator.

      Works like :meth:`throw_wait`
      but does so asynchronously.
      The spawned thread raises :exc:`WaitTimeoutError`
      when it times out.

      :rtype: threading.Thread
      :return:
         The created and running thread.

   .. method:: close()

      Equivalent to ``self.generator.close()``.


   .. method:: has_terminated()

      Check if the wrapped generator has terminated.

      :return bool:
         Whether the generator has terminated.

   .. method:: can_resume()

      Test if the generator can be resumed, i.e. is not running or closed.

      :return bool:
         Whether the generator can be resumed.

   .. method:: __call__()

      Alias for :meth:`with_strong_ref`.


.. class:: StrongGeneratorWrapper(generator, weak_generator=None, catch_stopiteration=True, debug=False)

   Wraps a generator and adds convenience features.

   Operates similar to :class:`WeakGeneratorWrapper`,
   except that it holds a strong reference to the generator.
   Use this class
   if you want to pass the generator wrapper itself around,
   so that the generator is not garbage-collected.

   .. note::

      Binding an instance if this in the generator's scope
      will create a circular reference.

   .. method:: __call__()

      Alias for :meth:`with_strong_ref`.


Exceptions
==========

.. class:: WaitTimeoutError

   Error class that is raised when a specified timeout is exceeded.
