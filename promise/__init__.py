import exceptions, sys, traceback, untwisted

# Differences from Twisted: Promises are also callbacks, whereas deferreds
# aren't, this eliminates .chainDeferred()

# "Callable" or "callback", anything that can be called
# "Callback" or variation on generator where .send() is .__call__(), a callable
# with .throw()
# "Promise"? a callback with .then().  By default .__call__() does nothing.
# It calls callbacks passed to .then().  It raises an exception if called
# twice.  By default .throw() raises the exception?  It calls .throw() on
# callbacks passed to .then()?

# Think promise is a monad, but what value is this perspective?
# http://www.valuedlessons.com/2008/01/monads-in-python-with-nice-syntax.html

class promise:
  trigger = False

  def __init__(ctx):
    ctx.callback = []

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

        # Don't worry about callback.traceback: Can't be without .args
        except AttributeError:
          pass

        callback.args = ctx.args
        ctx.args = callback,

        callback.kwds = ctx.kwds
        ctx.kwds = {}

        if ctx.callback:
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
        ctx.traceback = untwisted.final(untwisted.partial(sys.stderr.write, ''.join(traceback.format_stack(sys._getframe().f_back)) + traceback.format_exc()))

        ctx.args = sys.exc_info()
        ctx.kwds = {}

        continue

      if isinstance(result, promise):

        # Tail call optimization
        #result.then(ctx)

        try:
          ctx.traceback = result.traceback
          del result.traceback

        # Don't worry about ctx.traceback: del above
        except AttributeError:
          pass

        try:
          ctx.args = result.args
          result.args = ctx,

          ctx.kwds = result.kwds
          result.kwds = {}

        # Not yet triggered
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

  def throw(ctx, *args, **kwds):

    # Already triggered
    if ctx.trigger:
      raise StopIteration

    ctx.trigger = True

    #raise args
    if args:
      #type, value=None, traceback=None = args
      type, value, traceback = (lambda type, value=None, traceback=None: (type, value, traceback))(*args)
      try:
        raise type, value, traceback

      except:
        pass

    import traceback

    ctx.traceback = untwisted.final(untwisted.partial(sys.stderr.write, ''.join(traceback.format_stack(sys._getframe().f_back)) + traceback.format_exc()))

    ctx.args = args
    ctx.kwds = kwds

    ctx.propagate()

    return ctx

# Sequence is a callback.  An advantage is that it can replace a function or
# callback without maintaining two references, one to .push() and one to the
# sequence
class sequence:
  def __init__(ctx):
    ctx.consume = []
    ctx.produce = []

  def __call__(ctx, *args, **kwds):
    try:
      itm = ctx.consume.pop(0)

    except IndexError:
      itm = promise()
      ctx.produce.append(itm)

    itm(*args, **kwds)

    return ctx

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

# Join promises into one promise, which only propagates after all these
# promises are triggered.  join() supports a mixture of arguments which are and
# aren't promises.  Callbacks subscribed to the joined promise are called with
# one argument for each argument to join(): If the argument to join() was a
# promise then the argument to the callback is this promise's result, otherwise
# it's the original argument
#
# Join is like the following, except,
#
#  * this is infinitely recursive because @continuate depends on join()
#
#  * this isn't a generator function!  "yield" yields extra values from the
#    list comprehension - it doesn't form a generator function.  Bracketing the
#    list comprehension with "[]" solves this, however
#
# @continuate
# def join(*args, **kwds):
#   #return ...
#   raise StopIteration(*((yield itm) for itm in args), **kwds)
#
def join(*args, **kwds):
  try:
    #head, *rest = args
    head, rest = args[0], iter(args[1:])

  except IndexError:
    return promise()(*args, **kwds)

  args = []
  def callback(*nstArgs, **nstKwds):
    args.append(*nstArgs)
    kwds.update(nstKwds)

    try:
      result = rest.next()

    except exceptions.StopIteration:
      return promise()(*args, **kwds)

    ctx.callback.insert(0, callback)

    return result

  ctx = promise().then(callback)
  if isinstance(head, promise):
    head.then(ctx)

    return ctx

  return ctx(head)

# If continuate is a class, then wrapper (aka .__call__()) is either a method
# or a class, and neither a method nor a class behaves like a function when
# it's an attribute of another object.  The first argument of a method is
# always a continuate instance and the first argument of a class is wrapper
# (aka .__call__()) instance.  untwisted.ctxual() is a workaround, but a
# function is simpler
def continuate(cbl):

  # If cbl is a function and wrapper is a class then it doesn't behave like cbl
  # when it's an attribute of another object
  def wrapper(*args, **kwds):
    gnr = cbl(*args, **kwds)

    def callback(*args, **kwds):
      try:
        result = gnr.send(*args, **kwds)

      except exceptions.StopIteration as e:
        return join(*e.args or (None,), **getattr(e, 'kwds', {}))

      ctx.callback.insert(0, callback)

      return result

    @untwisted.partial(setattr, callback, 'throw')
    def throw(*args, **kwds):
      try:
        result = gnr.throw(*args, **kwds)

      except exceptions.StopIteration as e:
        return join(*e.args or (None,), **getattr(e, 'kwds', {}))

      ctx.callback.insert(0, callback)

      return result

    ctx = promise().then(callback)

    # gnr.send(None)
    return ctx(None)

  return wrapper

def nowThen(ctx, now=lambda *args, **kwds: promise()(*args, **kwds), then=lambda *args, **kwds: promise()(*args, **kwds)):
  wrapper = lambda *args, **kwds: callback(*args, **kwds)

  callback = now
  try:
    wrapper.throw = now.throw

  except AttributeError:
    pass

  try:
    return ctx.then(wrapper)

  finally:
    callback = then
    try:
      wrapper.throw = then.throw

    except AttributeError:
      try:
        del wrapper.throw

      except AttributeError:
        pass

# Variation of untwisted.compose() which only calls arguments after the result
# of the previous argument is triggered, if the result of the previous argument
# was a promise
#
# compose(etc., third, second, first) is point free (pointless) variation of
# the following,
#
# lambda *args, **kwds: promise()(*args, **kwds).then(first).then(second).then(third).then(etc.)
#
compose = lambda *args: lambda *nstArgs, **nstKwds: reduce(promise.then, reversed(args), promise())(*nstArgs, **nstKwds)
