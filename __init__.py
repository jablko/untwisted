import weakref

call = lambda callable: callable()

# Callback is called after there are no references to this final instance, or
# after this final instance is garbage collected if it's part of a collectable
# reference cycle.  Callback isn't called in the following rare (hopefully)
# cases,
#
#  * Exotic situations like when the program is killed by a signal not handled
#    by Python, when a Python fatal internal error is detected, or when
#    os._exit() is called
#
#  * There's an uncollectable reference to this final instance,
#    http://docs.python.org/reference/datamodel.html#object.__del__
#
#  * The weak reference instance is itself part of a circular reference
#
# Maintain references to weak references or they get destroyed before final
# instances - use weak dictionary to avoid memory leak.  Maintaining reference
# as final instance property fails in case final instance is part of a
# collectable reference cycle - maybe in that case weak reference property gets
# destroyed before final instance?
#
# http://jdbates.blogspot.com/2011/04/in-python-how-can-you-reliably-call.html

ref = weakref.WeakKeyDictionary()

class final:
  def cancel(ctx):
    del ref[ctx]

  def __init__(ctx, callback):
    ref[ctx] = weakref.ref(ctx, lambda ref: callback())
