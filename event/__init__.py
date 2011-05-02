import functools, sys, traceback, untwisted

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
  def propagate(ctx):
    while True:
      try:
        callback = ctx.callback.pop(0)

      # No callback
      except IndexError:
        return ctx

      try:
        result = ctx.next(callback)

        try:
          ctx.traceback.cancel()

        except AttributeError:
          pass

        ctx.next = lambda callback: callback(result)

      #except as ctx.data:
      except:
        ctx.traceback = untwisted.final(functools.partial(sys.stderr.write, ''.join(traceback.format_stack(sys._getframe().f_back)) + traceback.format_exc()))

        ctx.next = lambda callback: callback.throw(sys.exc_info()[1])

  def __call__(ctx, *args, **kwds):

    # Already triggered
    if hasattr(ctx, 'next'):
      raise StopIteration

    ctx.next = lambda callback: callback(*args, **kwds)
    ctx.propagate()

    return ctx

  def connect(ctx, callback):
    ctx.callback.append(callback)

    # Already triggered
    if hasattr(ctx, 'next'):
      ctx.propagate()

    return ctx

  def __init__(ctx):
    ctx.callback = []

  def throw(ctx, *args, **kwds):

    # Already triggered
    if hasattr(ctx, 'next'):
      raise StopIteration

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

    ctx.next = lambda callback: callback.throw(*args, **kwds)
    ctx.propagate()

    return ctx

# Sequence is a callback.  An advantage is that it can replace a function or
# callback without maintaining two references, one to .push() and one to the
# sequence
class sequence:
  def __call__(ctx, *args, **kwds):
    try:
      item = ctx.consume.pop(0)

    except IndexError:
      item = event()
      ctx.produce.append(item)

    item(*args, **kwds)

    return ctx

  def __init__(ctx):
    ctx.consume = []
    ctx.produce = []

  def shift(ctx):
    try:
      return ctx.produce.pop(0)

    except IndexError:
      item = event()
      ctx.consume.append(item)

      return item

def connect(callable):
  def wrapper(*args, **kwds):
    generator = callable(*args, **kwds)

    try:

      # TODO Tail call elimination

      @untwisted.call
      class callback:
        def __call__(ctx, *args, **kwds):
          try:
            return generator.send(*args, **kwds).connect(ctx)

          except StopIteration as e:
            try:
              return e.args[0]

            except IndexError:
              pass

        def throw(ctx, e):
          try:
            return generator.throw(e).connect(ctx)

          except StopIteration as e:
            try:
              return e.args[0]

            except IndexError:
              pass

      return generator.next().connect(callback)

    except StopIteration as e:
      try:
        return e.args[0]

      except IndexError:
        pass

  return wrapper
