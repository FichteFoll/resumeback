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

Documentation
=============

https://fichtefoll.github.io/resumeback/


Installation
============

.. code-block:: shell

    $ pip install resumeback


Example Usage
=============

.. code-block:: python

    from threading import Thread
    from resumeback import send_self

    def ask_for_user_input(question, on_done):
        def watcher():
            result = input(question)
            on_done(result)

        Thread(target=watcher).start()

    @send_self
    def main(this):  # "this" is a reference to the created generator instance
        arbitrary_value = 10

        # Yield pauses execution until one of the generator methods is called,
        # such as `.send`, which we provide as the callback parameter.
        number = yield ask_for_user_input("Please enter a number", this.send)
        number = int(number)
        print("Result:", number * arbitrary_value)

    if __name__ == "__main__":
        main()


Development
===========

Requires Python, poetry, and GNU Make.

Use ``make help`` to show the available targets.

- poetry__ is used for dependency and virtualenv management.
- tox__ is used as a test runner for multiple isolated environments.
- flake8__ is used for code linting.
- `Github Actions`__ are used for CI.

__ https://python-poetry.org/
__ https://tox.readthedocs.io/
__ https://flake8.readthedocs.io/
__ https://github.com/features/actions


Acknowledgements
================

Project started initially after a `forum post`__ from `@Varriount`__
on the Sublime Text forum.
I just took his idea "to the next (abstraction) level"
and made it more convenient to use.

__ https://forum.sublimetext.com/t/using-generators-for-fun-and-profit-utility-for-developers/14618
__ https://github.com/Varriount
