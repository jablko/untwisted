import exceptions, functools, sys, traceback, untwisted

# Differences from Twisted: Promises are also callbacks, whereas deferreds
# aren't, this eliminates .chainDeferred()

# "Callback" or "callable", anything that can be called
# "Callback" or "coroutine", or variation on coroutine where .send() is
# .__call__(), a callable with .throw()
# "Promise"? a callback with .then().  By default .__call__() does nothing.
# It calls callbacks passed to .then().  It raises an exception if called
# twice.  By default .throw() raises the exception?  It calls .throw() on
# callbacks passed to .then()?
class promise:
  def then(ctx, callback):
    ctx.callback.append(callback)

    # Ready to propagate
    if hasattr(ctx, 'args'):
      ctx.propagate()

    return ctx

  def propagate(ctx):
    while True:
      try:
        callback = ctx.callback.pop(0)

      # No callback
      except IndexError:
        return ctx

      if isinstance(callback, promise):

        # Already triggered
        if hasattr(callback, 'args'):
          raise StopIteration

        callback.trigger = True

        try:
          callback.traceback = ctx.traceback
          del ctx.traceback

        except AttributeError:
          pass

        callback.args = ctx.args
        ctx.args = ()

        callback.kwds = ctx.kwds
        ctx.kwds = {}

        if len(ctx.callback):
          callback.propagate()

        # Tail call optimization
        else:
          ctx = callback

        continue

      # Skip if callback has no .throw()
      if hasattr(ctx, 'traceback'):
        try:
          callback = callback.throw

        except AttributeError:
          continue

        ctx.traceback.cancel()
        del ctx.traceback

      args = ctx.args
      del ctx.args

      kwds = ctx.kwds
      del ctx.kwds

      try:
        result = callback(*args, **kwds)

      except:
        ctx.traceback = untwisted.final(functools.partial(sys.stderr.write, ''.join(traceback.format_stack(sys._getframe().f_back)) + traceback.format_exc()))

        ctx.args = sys.exc_info()
        ctx.kwds = {}

        continue

      if isinstance(result, promise):

        # Tail call optimization
        #result.then(ctx)

        try:
          ctx.traceback = result.traceback
          del result.traceback

        except AttributeError:
          pass

        try:
          ctx.args = result.args
          result.args = ()

          ctx.kwds = result.kwds
          result.kwds = {}

        except AttributeError:
          result.callback.append(ctx)

          return ctx

        continue

      ctx.args = result,
      ctx.kwds = {}

  def __call__(ctx, *args, **kwds):

    # Already triggered
    if ctx.trigger:
      raise StopIteration

    ctx.trigger = True

    ctx.args = args
    ctx.kwds = kwds

    ctx.propagate()

    return ctx

  def __init__(ctx):
    ctx.callback = []
    ctx.trigger = False

  def throw(ctx, *args, **kwds):

    # Already triggered
    if ctx.trigger:
      raise StopIteration

    ctx.trigger = True

    #raise args
    if len(args):
      #type, value=None, traceback=None = *args
      type, value, traceback = (lambda type, value=None, traceback=None: (type, value, traceback))(*args)
      try:
        raise type, value, traceback

      except:
        pass

    import traceback

    ctx.traceback = untwisted.final(functools.partial(sys.stderr.write, ''.join(traceback.format_stack(sys._getframe().f_back)) + traceback.format_exc()))

    ctx.args = args
    ctx.kwds = kwds

    ctx.propagate()

    return ctx

# Sequence is a callback.  An advantage is that it can replace a function or
# callback without maintaining two references, one to .push() and one to the
# sequence
class sequence:
  def __call__(ctx, *args, **kwds):
    try:
      itm = ctx.consume.pop(0)

    except IndexError:
      itm = promise()
      ctx.produce.append(itm)

    itm(*args, **kwds)

    return ctx

  def __init__(ctx):
    ctx.consume = []
    ctx.produce = []

  def shift(ctx):
    try:
      return ctx.produce.pop(0)

    except IndexError:
      itm = promise()
      ctx.consume.append(itm)

      return itm

class StopIteration(exceptions.StopIteration):
  def __init__(ctx, *args, **kwds):
    exceptions.StopIteration.__init__(ctx, *args)

    ctx.kwds = kwds

# Join is a promise.  When called, its arguments may be other promises.  It
# propagates only after all these promises are triggered and calls callbacks
# with the results of all these promises
#
# Join is like the following, except,
#
#  * this is infinitely recursive because continuate calls join
#
#  * this isn't a generator function!  "yield" yields extra values from the
#    list comprehension - it doesn't form a generator function
#
# @continuate
# def join(*args, **kwds):
#   raise StopIteration(((yield itm) for itm in args), **kwds)
#
class join(promise):
  def __call__(ctx, *args, **kwds):

    # Already triggered
    if ctx.trigger:
      raise StopIteration

    ctx.trigger = True

    try:
      #head, *rest = args
      head, rest = args[0], args[1:]

      # Can iterate with iterator or list, not tuple
      rest = list(rest)

      args = []
      def callback(*argsItm, **kwdsItm):
        try:
          args.append(*argsItm)

        except TypeError:
          args.append(argsItm)

        kwds.update(*kwdsItm)

        try:
          itm = rest.pop(0)

        except IndexError:
          return promise()(*args, **kwds)

        ctx.callback.insert(0, callback)

        return itm

      ctx.callback.insert(0, callback)

      if isinstance(head, promise):
        head.then(ctx)

        return ctx

      ctx.args = head,
      ctx.kwds = {}

    except IndexError:
      ctx.args = args
      ctx.kwds = kwds

    ctx.propagate()

    return ctx

# If continuate is a class, then wrapper (aka .__call__()) is either a method
# or a class, and neither a method nor a class behaves like a function if it's
# an attribute of another object.  The first argument of a method is always a
# continuate instance and the first argument of a class is wrapper (aka
# .__call__()) instance.  untwisted.ctxual is a workaround, but a function is
# simpler
def continuate(cbl):

  # If cbl is a function and wrapper is a class then it doesn't behave like cbl
  # if it's an attribute of another object
  def wrapper(*args, **kwds):
    gnr = cbl(*args, **kwds)
    result = promise()

    @result.then
    @untwisted.call
    class _:
      def __call__(ctx, *args, **kwds):
        try:
          itm = gnr.send(*args, **kwds)

        except exceptions.StopIteration as e:
          return join()(*e.args if len(e.args) else (None,), **getattr(e, 'kwds', {}))

        result.callback.insert(0, ctx)

        return itm

      def throw(ctx, *args, **kwds):
        try:
          itm = gnr.throw(*args, **kwds)

        except exceptions.StopIteration as e:
          return join()(*e.args if len(e.args) else (None,), **getattr(e, 'kwds', {}))

        result.callback.insert(0, ctx)

        return itm

    # gnr.send(None)
    return result(None)

  return wrapper

def nowThen(result, now=lambda *args, **kwds: promise()(*args, **kwds), then=lambda *args, **kwds: promise()(*args, **kwds)):
  wrapper = lambda *args, **kwds: callback(*args, **kwds)

  callback = now
  try:
    wrapper.throw = now.throw

  except AttributeError:
    pass

  try:
    return result.then(wrapper)

  finally:
    callback = then
    try:
      wrapper.throw = then.throw

    except AttributeError:
      try:
        del wrapper.throw

      except AttributeError:
        pass
