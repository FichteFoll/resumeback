==============
 Introduction
==============

A Python 3 library for using callbacks to resume your code.

``resumeback`` provides a utility function decorator
that enables using callback-based interfaces
in **a single line of execution**
-- a single function.

The source code is available on GitHub under the MIT license:
https://github.com/FichteFoll/resumeback


.. contents::

.. toctree::
   :maxdepth: 2

   reference


Installation
============

.. code-block:: shell

    $ pip install resumeback


Usage
=====

:func:`resumeback.send_self`'s mechanic of providing a generator function
with a handle to its running instance
allows for better flow control
using callback-based interfaces.
Essentially, it enables *a single line of execution*.

Following is a function that uses an asynchronous callback mechanism
to signal that user input has been made:

.. code-block:: python

    from threading import Thread

    def ask_for_user_input(question, on_done):
        def watcher():
            result = input(question)
            on_done(result)

        Thread(target=watcher).start()

The *traditional* way of using a function like ``ask_for_user_input`` would be
to define a function of some way,
either as a closure or using :func:`functools.partial`,
so that we can preserve the state we already accumulated
prior to executing said function.

For example, like so:

.. code-block:: python

    def main():
        arbitrary_value = 10

        def on_done(number):
            number = str(number)
            print("Result:", number * arbitrary_value)

        ask_for_user_input("Please enter a number", on_done)

Because Python does not have multi-line inline functions,
this is rather awkward,
since we are jumping from the function call of ``ask_for_user_input``
back to our previously defined function ``on_done``
-- which is only ever going to be called once in this context.

However, using :func:`resumeback.send_self`,
we can *flatten our line of execution*
by passing a callback to resume execution in our original function:

.. code-block:: python

    from resumeback import send_self

    @send_self
    def main(this):  # "this" is a reference to the created generator instance
        arbitrary_value = 10

        # Yield pauses execution until one of the generator methods is called,
        # such as `.send`, which we provide as the callback parameter.
        number = yield ask_for_user_input("Please enter a number", this.send)
        number = int(number)
        print("Result:", number * arbitrary_value)

The function decorated by :func:`~resumeback.send_self`
will be called with the wrapper to the created generator instance
as the first parameter.


Methods
-------

The :func:`~resumeback.send_self` decorator can be used on methods,
classmethods and staticmethods as well.
For methods, they behave as you would expect.
For class- or staticmethods, you must ensure
that you put the method decorator *above* :func:`~resumeback.send_self`.

.. code-block:: python

    from resumeback import send_self

    class Class:
        @send_self
        def method(this, self):
            pass  # do things with `self`

        @classmethod
        @send_self
        def clsmethod(this, cls):
            pass  # do things with `cls`


Generators
----------

:func:`resumeback.send_self` operates on generators
and their possibility of sending arbitrary data to them
wherever they paused execution.
Calling a generator function decorated with ``@resumeback.send_self``
results in the function receiving the created generator instance object
as its first argument.
The generator may then delegate its execution environment
however it desires.

For this delegation,
generators in Python provide four methods for interacting with them:

1. **next** -- to just resume execution (used as ``next(generator)``)
2. **send** -- to resume execution and additionally send any value to it
3. **throw** -- to raise an exception at the position the generator paused
4. **close** -- to close the generator

Note that any remaining ``finally`` blocks wrapping a paused ``yield``
will be called when the generator is deleted.


The Generator Wrapper
---------------------

Instead of being called with the generator instance directly,
it is wrapped in a convenience class
named :class:`~resumeback.WeakGeneratorWrapper`.

The wrapper wraps all interacting methods
and catches :exc:`StopIteration` exceptions,
so that termination of the generator
(due to returning a value or just reaching the end)
does not raise an exception in the caller's code.
This can be disabled dynamically.

It further only holds a weak reference to the generator,
which prevents reference cycles
due to the generator not holding a reference to itself.
When accessing a resuming function to provide as a callback,
a strong reference for the generator is created
to ensure it does not get cleaned up
while it waits for that to be called.
This is but an optimization.
A strongly referencing wrapper is available on-demand.


Preventing Race Conditions
--------------------------

Because threads can be interrupted at any point in a non-atomic operation,
it is possible that a generator could be attempted to be resumed
before it has paused from the following ``yield`` keyword.
To prevent this, the wrapper provides ``*_wait`` methods.
These behave exactly like their normal counterparts
with the addition of a ``timeout`` parameter
and a busy poll for whether the generator is in a paused state.

However, when the provided callback to resume the generator is called immediately,
it will never have had the chance to pause itself.
For convenience in these situations,
the wrapper object provides ``*_wait_async`` methods
that spawn a separate thread to perform the polling in.
The generator will then be resumed on that thread.


Subgenerators
-------------

You can embed subgenerators into the send_self-decorated function.
The returned value of the subgenerator
will become the value of the ``yield from`` expression.
See the `Python documentation for yield expressions`__ for more details.

__ https://docs.python.org/3/reference/expressions.html#yield-expressions

When embedding functions that have been decorated with :func:`~resumeback.send_self` already,
you can access its :attr:`~resumeback.send_self.func` attribute
to obtain the wrapped generator function.
Make sure to provide the wrapper as the first parameter.

.. code-block:: python

    def get_number(this):
        number = yield ask_for_user_input("Please enter a number", this.send)
        return number

    @send_self
    def print_num(this):
        number = yield from get_number(this)
        print(number)
        return number  # allows caller to retrieve this value

    @send_self
    def print_plus_10(this):
        number = yield from print_num.func(this)
        number += 10
        print(number)
        return number
