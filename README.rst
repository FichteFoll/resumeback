============
 resumeback
============

.. image:: https://travis-ci.org/FichteFoll/resumeback.svg
   :target: https://travis-ci.org/FichteFoll/resumeback

.. image:: https://coveralls.io/repos/FichteFoll/resumeback/badge.svg
   :target: https://coveralls.io/github/FichteFoll/resumeback?branch=master

.. image:: https://img.shields.io/pypi/v/resumeback.svg
    :target: https://pypi.python.org/pypi/resumeback

.. image:: https://img.shields.io/pypi/pyversions/resumeback.svg
    :target: https://pypi.python.org/pypi/resumeback/

.. .. image:: https://img.shields.io/pypi/dd/resumeback.svg
..     :target: https://pypi.python.org/pypi/resumeback/

A Python library for using callbacks to resume your code.

``resumeback`` provides a utility function decorator
that enables using callback-based interfaces
in **a single line of execution**
-- a single function.

Full docs are available here: http://fichtefoll.github.io/resumeback/


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
either as a closure or using ``functools.partial`` so that we can preserve
the state we already accumulated prior to executing said function.

For example like so:

.. code-block:: python

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
by passing a callback to resume execution in our original function:

.. code-block:: python

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


Acknowledgements
================

Project started initially after a `forum post`__ from `@Varriount`__
on the Sublime Text forum.
I just took his idea "to the next (abstraction) level"
and made it more convenient to use.

__ http://www.sublimetext.com/forum/viewtopic.php?f=6&t=17671
__ https://github.com/Varriount