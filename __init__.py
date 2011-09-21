import weakref

call = lambda cbl: cbl()

def compose(*args):
  #*rest, head = args
  head, rest = (lambda head, *rest: (head, rest))(*reversed(args))

  return lambda *args, **kwds: reduce(lambda result, cbl: cbl(result), rest, head(*args, **kwds))

# Give a class access to its dynamic context, e.g.
#
#   class outer:
#     class inner:
#       class __metaclass__(type):
#         __get__ = ctxual
#
#   instance = outer()
#   instance is instance.inner.ctx # True
#
# A subclass is generated each time the class (inner) is accessed with a unique
# dynamic context (instance).  The same subclass must be returned each time the
# class is accessed with the same dynamic context, such that:
#
#   instance.inner.sample = 'Sample'
#
#   # If the same subclass isn't returned then this might raise an AttributeError
#   instance.inner.sample # 'Sample'
#
# This is achieved with a mapping from class and dynamic context to subclass.
# To avoid leaking memory, we make weak references to class and dynamic
# context.  Subclass references class and dynamic context (this is our goal) so
# if we don't also make weak reference to subclass, then it, class, and dynamic
# context won't get finalized before mapping is finalized
#
# Recycle mapping when class or dynamic context get finalized.  To simplify,
# recycle mapping when subclass is finalized.  Because subclass references
# class and dynamic context, this never happens later than class or dynamic
# context get finalized.  Only difference is that after subclass is finalized,
# mapping is recycled vs. a broken weak reference

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
# cases:
#
#   * Exotic situations like when the program is killed by a signal not handled
#     by Python, when a Python fatal internal error is detected, or when
#     os._exit() is called
#
#   * There's an uncollectable reference to this final instance,
#     http://docs.python.org/reference/datamodel.html#object.__del__
#
#   * The weak reference instance is itself part of a circular reference
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

class oneMany:
  def __init__(ctx, *args):
    ctx.asdf = list(args)

  def __getattr__(ctx, name):
    try:
      return getattr(ctx.asdf, name)

    except AttributeError:
      asdf, = ctx.asdf

      return getattr(asdf, name)

  def __getitem__(ctx, name):
    try:
      return ctx.asdf[name]

    except TypeError:
      asdf, = ctx.asdf

      return asdf[name]

class manyMap:
  def __init__(ctx, *args, **kwds):
    ctx.asdf = dict(*args, **kwds)

  def __getattr__(ctx, name):
    try:
      return getattr(ctx.asdf, name)

    except AttributeError:
      return ctx.asdf[name]

  def __getitem__(ctx, name):
    try:
      return ctx.asdf[name]

    except KeyError:
      return getattr(ctx.asdf, name)

  __iter__ = lambda ctx: ctx.asdf.iteritems()

  def append(ctx, key, value):
    try:
      ctx.asdf[key].append(value)

    except KeyError:
      ctx.asdf[key] = oneMany(value)

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
