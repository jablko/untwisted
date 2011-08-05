import weakref

call = lambda cbl: cbl()

def compose(*args):
  #*rest, head = args
  head, rest = (lambda head, *rest: (head, rest))(*reversed(args))

  return lambda *args, **kwds: reduce(lambda result, cbl: cbl(result), rest, head(*args, **kwds))

# http://jdbates.blogspot.com/2011/07/in-python-how-can-you-associate-one.html
cache = weakref.WeakValueDictionary()
def ctxual(ctx, instance, *_):
  try:
    key = weakref.ref(ctx), weakref.ref(instance)

  except TypeError:
    key = weakref.ref(ctx), instance

  try:
    return cache[key]

  except KeyError:
    result = cache[key] = type(ctx)(ctx.__name__, (ctx,), { 'ctx': instance })

    return result

def each(cbl):
  gnr = cbl()
  gnr.next()

  # gnr.send() not a descriptor,
  # http://docs.python.org/reference/datamodel.html#descriptors
  def result(*args, **kwds):
    try:
      head, = args

    except ValueError:
      return gnr.send(args, **kwds)

    return gnr.send(head, **kwds)

  result.throw = gnr.throw

  return result

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
  def result(*args, **kwds):
    gnr = cbl()
    gnr.next()

    try:
      gnr.send(*args, **kwds)

    except StopIteration as e:
      if e.args:
        try:
          head, = e.args

        except ValueError:
          return e.args

        return head

  @partial(setattr, result, 'throw')
  def throw(*args, **kwds):
    gnr = cbl()
    gnr.next()

    try:
      gnr.throw(*args, **kwds)

    except StopIteration as e:
      if e.args:
        try:
          head, = e.args

        except ValueError:
          return e.args

        return head

  return result

# http://jdbates.blogspot.com/2011/04/ow-ow-ow-python-why-do-you-hurt-so-hard.html
identity = lambda ctx: ctx

# functools.partial() breaks descriptor,
# http://docs.python.org/reference/datamodel.html#descriptors
class partial:
  __metaclass__ = type

  # No **kwds because, TypeError: unhashable type: 'dict'
  def __get__(ctx, instance=None, owner=None):
    try:
      return cache[ctx, instance, owner]

    except KeyError:
      result = cache[ctx, instance, owner] = partial(ctx.cbl.__get__(instance, owner), *ctx.args, **ctx.kwds)

      return result

  def __init__(ctx, cbl, *args, **kwds):
    ctx.cbl = cbl
    ctx.args = args
    ctx.kwds = kwds

  def __call__(ctx, *args, **kwds):
    totalArgs = list(ctx.args)
    totalArgs.extend(args)

    totalKwds = dict(ctx.kwds)
    totalKwds.update(kwds)

    return ctx.cbl(*totalArgs, **totalKwds)

@call
class wildcard:
  __contains__ = lambda *args, **kwds: True
