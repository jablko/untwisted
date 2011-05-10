import exceptions, functools, sys, traceback, untwisted

# Differences from Twisted: Events are also callbacks, whereas deferreds
# aren't, this eliminates .chainDeferred()

# "Callback" or "callable", anything that can be called
# "Callback" or "coroutine", or variation on coroutine where .send() is
# .__call__(), a callable with .throw()
# "Event"? a callback with .connect().  By default .__call__() does nothing.
# It calls callbacks passed to .connect().  It raises an exception if called
# twice.  By default .throw() raises the exception?  It calls .throw() on
# callbacks passed to .connect()?
class event:
  def connect(ctx, callback):
    ctx.callback.append(callback)

    # Ready to propagate
    if hasattr(ctx, 'advance'):
      ctx.propagate()

    return ctx

  def propagate(ctx):
    while True:
      try:
        callback = ctx.callback.pop(0)

      # No callback
      except IndexError:
        return ctx

      if isinstance(callback, event):

        # Already triggered
        if hasattr(callback, 'advance'):
          raise StopIteration

        callback.trigger = True

        callback.advance = ctx.advance
        callback.propagate()

        ctx.advance = lambda callback: callback()

        continue

      # Don't propagate (on ctx.connect())
      advance = ctx.advance
      del ctx.advance

      try:
        result = advance(callback)

      except:
        final = untwisted.final(functools.partial(sys.stderr.write, ''.join(traceback.format_stack(sys._getframe().f_back)) + traceback.format_exc()))

        info = sys.exc_info()
        ctx.advance = lambda callback: (final.cancel(), callback.throw(*info))[-1]

        continue

      if isinstance(result, event):
        result.connect(ctx)

        return ctx

      ctx.advance = lambda callback: callback(result)

  def __call__(ctx, *args, **kwds):

    # Already triggered
    if ctx.trigger:
      raise StopIteration

    ctx.trigger = True

    try:
      connect, = args
      if isinstance(connect, event):
        connect.connect(ctx)

        return ctx

    except ValueError:
      pass

    ctx.advance = lambda callback: callback(*args, **kwds)
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

    final = untwisted.final(functools.partial(sys.stderr.write, ''.join(traceback.format_stack(sys._getframe().f_back)) + traceback.format_exc()))

    ctx.advance = lambda callback: (final.cancel(), callback.throw(*args, **kwds))[-1]
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
      itm = event()
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
      itm = event()
      ctx.consume.append(itm)

      return itm

class StopIteration(exceptions.StopIteration):
  def __init__(ctx, *args, **kwds):
    exceptions.StopIteration.__init__(ctx, *args)

    ctx.kwds = kwds

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
    result = event()

    # TODO Tail call elimination

    @result.connect
    @untwisted.call
    class ignore:
      def __call__(ctx, *args, **kwds):
        try:
          itm = gnr.send(*args, **kwds)

        except exceptions.StopIteration as e:
          try:
            return event()(*e.args, **e.kwds)

          except AttributeError:
            return event()(*e.args)

        result.callback.insert(0, ctx)

        return itm

      def throw(ctx, *args, **kwds):
        try:
          itm = gnr.throw(*args, **kwds)

        except exceptions.StopIteration as e:
          try:
            return event()(*e.args, **e.kwds)

          except AttributeError:
            return event()(*e.args)

        result.callback.insert(0, ctx)

        return itm

    # gnr.send(None)
    return result(None)

  return wrapper
