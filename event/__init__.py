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

  @untwisted.call
  class advance(object):
    __get__ = untwisted.ctxual

    def __call__(ctx, *args, **kwds):

      # *args is guaranteed not to be an event because advance is only ever
      # connected to other event, and event never callback with event
      ctx.ctx.next = lambda callback: callback(*args, **kwds)
      ctx.ctx.propagate()

      return ctx.ctx

    def throw(ctx, *args, **kwds):
      #raise args
      if len(args):
        #type, value=None, traceback=None = *args
        type, value, traceback = (lambda type, value=None, traceback=None: (type, value, traceback))(*args)
        try:
          raise type, value, traceback

        except:
          pass

      import traceback

      ctx.ctx.traceback = untwisted.final(functools.partial(sys.stderr.write, ''.join(traceback.format_stack(sys._getframe().f_back)) + traceback.format_exc()))

      ctx.ctx.next = lambda callback: callback.throw(*args, **kwds)
      ctx.ctx.propagate()

      return ctx.ctx

  def propagate(ctx):
    while True:
      try:
        callback = ctx.callback.pop(0)

      # No callback
      except IndexError:
        return ctx

      try:
        ctx.traceback.cancel()

      except AttributeError:
        pass

      try:
        result = ctx.next(callback)
        if not isinstance(callback, event) and not isinstance(callback, event.advance.__class__) and isinstance(result, event):

          # Don't propagate (on ctx.connect()) until callback
          del ctx.next

          result.connect(ctx.advance)

          return ctx

        ctx.next = lambda callback: callback(result)

      except:
        ctx.traceback = untwisted.final(functools.partial(sys.stderr.write, ''.join(traceback.format_stack(sys._getframe().f_back)) + traceback.format_exc()))

        info = sys.exc_info()
        ctx.next = lambda callback: callback.throw(*info)

  def __call__(ctx, *args, **kwds):

    # Already triggered
    if ctx.trigger:
      raise StopIteration

    ctx.trigger = True

    try:
      connect, = args
      if isinstance(connect, event):
        connect.connect(ctx.advance)

        return ctx

    except ValueError:
      pass

    ctx.advance(*args, **kwds)

    return ctx

  def connect(ctx, callback):
    ctx.callback.append(callback)

    # Ready to propagate
    if hasattr(ctx, 'next'):
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

    ctx.advance.throw(*args, **kwds)

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
              #value, *result = e.args
              value, result = e.args[0], e.args[1:]
              if len(result):
                return value, + result

              return value

            except IndexError:
              pass

        def throw(ctx, *args, **kwds):
          try:
            return generator.throw(*args, **kwds).connect(ctx)

          except StopIteration as e:
            try:
              #value, *result = e.args
              value, result = e.args[0], e.args[1:]
              if len(result):
                return value, + result

              return value

            except IndexError:
              pass

      return generator.next().connect(callback)

    except StopIteration as e:
      try:
        #value, *result = e.args
        value, result = e.args[0], e.args[1:]
        if len(result):
          return value, + result

        return value

      except IndexError:
        pass

  return wrapper
