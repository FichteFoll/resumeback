==============
 Introduction
==============

``resumeback`` provides a utility function decorator
that enables using callback-based interfaces
in **a single line of execution**
-- a single function.

.. toctree::
   :maxdepth: 2

   index
   reference

Installation
============

.. code-block:: shell

    $ pip install resumeback


Usage
=====

``resumeback.send_self``'s mechanic of sending a generator function
a handle to itself
is what allows for better flow control
using callback-based interfaces.
Essentially, it enables *a single line of execution*.

Following is a function that uses an asynchronous callback mechanism
to signal that user input has been made::

   from threading import Thread

   def ask_for_user_input(question, on_done):
       def watcher():
           result = input(question)
           on_done(result)

       Thread(target=watcher).start()

The *traditional* way of using a function like ``ask_for_user_input`` would be
to define a function of some way,
either as a closure or using ``functools.partial`` so that we can preserve
the state we already accumulated prior to executing said function.

For example like so::

   def main():
       arbitrary_value = 10

       def on_done(number):
           number = str(number)
           print("Result:", number * arbitrary_value)

       ask_for_user_input("Please enter a number", on_done)

Because Python does not have multi-line inline functions,
this is rather awkward,
because we are jumping from the function call of ``ask_for_user_input``
back to our previously defined function ``on_done``
-- which is only ever going to be called once in this context.

However, using ``resumeback.send_self``,
we can do something to *flatten our line of execution*
by passing a callback to resume execution in our original function::

   from resumeback import send_self

   @send_self
   def main():
       this = yield  # "this" is now a reference to the just-created generator
       arbitrary_value = 10

       # Yield pauses execution until one of the generator methods is called,
       # such as `.send`, which we provide as the callback parameter.
       number = yield ask_for_user_input("Please enter a number", this.send)
       number = str(number)
       print("Result:", number * arbitrary_value)


How it works
============

``resumeback.send_self`` operates on generators
and their possibility of sending arbitrary data to them
whereever they paused execution.
Upon calling a generator function decorated with ``@resumeback.send_self``,
it is executed until the first ``yield`` statement.
Immediately following,
the generator gets sent a wrapper to itself so it may delegate its execution
environment however it wishes.

Generators in Python provide four methods for interacting with them:

1. next -- to just resume execution
   (this is available on Python 3 via ``next(generator)``)
2. send -- to resume execution and additionally send any value to it
3. throw -- to raise an exception at the position the generator paused
4. close -- to close the generator

For the first three methods,
the wrapper additionally defines ``*_wait`` method variants,
which will block execution until the generator can actually be resumed,
and ``*_wait_async`` variants to also wait until the generator can be resumed,
but do so in a non-blocking way.

Additionally,
the wrapper catches ``StopIteration`` exceptions in these three methods,
so that termination of the generator
(due to returning a value or just reaching the end)
does not raise an exception in the caller's code,
which is most likely a function like ``ask_for_user_input``.
You can disable this whenever you want.

And finally,
the wrapper contains a weak reference to the generator,
which prevents reference cycles
due to the generator not holding a reference to itself.
This is but an optimization.


Code
====

The code is available on github: https://github.com/FichteFoll/resumeback

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
