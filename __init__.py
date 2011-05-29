import functools, weakref

call = lambda cbl: cbl()

cache = weakref.WeakValueDictionary()
def ctxual(ctx, instance, *args):
  try:
    return cache[ctx, instance]

  except KeyError:
    result = cache[ctx, instance] = type(ctx)(ctx.__name__, (ctx,), { 'ctx': instance })

    return result

def each(cbl):
  gnr = cbl()
  gnr.next()

  # gnr.send() not a descriptor,
  # http://docs.python.org/reference/datamodel.html#descriptors
  wrapper = lambda *args, **kwds: gnr.send(*args, **kwds)
  wrapper.throw = gnr.throw

  return wrapper

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

def head(cbl):
  def wrapper(*args, **kwds):
    gnr = cbl()
    gnr.next()

    try:
      gnr.send(*args, **kwds)

    except StopIteration as e:
      try:
        #head, *rest = e.args
        head, rest = e.args[0], e.args[1:]
        if len(rest):
          return (head,) + rest

        return head

      except IndexError:
        pass

  @functools.partial(setattr, wrapper, 'throw')
  def throw(*args, **kwds):
    gnr = cbl()
    gnr.next()

    try:
      gnr.throw(*args, **kwds)

    except StopIteration as e:
      try:
        #head, *rest = e.args
        head, rest = e.args[0], e.args[1:]
        if len(rest):
          return (head,) + rest

        return head

      except IndexError:
        pass

  return wrapper

# http://jdbates.blogspot.com/2011/04/ow-ow-ow-python-why-do-you-hurt-so-hard.html
def identity(head, *rest):
  if len(rest):
    return (head,) + rest

  return head
