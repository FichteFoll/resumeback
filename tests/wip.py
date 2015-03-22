import sys
import threading
import time
import weakref

import sublime
import sublime_plugin

from ..send_self import send_self

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
            print("caught and returned:", ret)  # should be the above message
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
