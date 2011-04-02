import functools, sys

# Differences from Twisted: Events are also callbacks, whereas deferreds
# aren't, this eliminates .chainDeferred()

# "Callback" or "callable", anything that can be called
# "Callback" or "coroutine", or variation on coroutine where .send() is
# .__call__(), a callable with .throw()
# "Event"? a callback with .connect().  By default .__call__() does nothing.
# It calls callbacks passed to .connect().  It raises an exception if called
# twice.  By default .throw() raises the exception?  It calls .throw() on
# callbacks passed to .connect()?
class Event:
  def propagate(self):
    while True:
      try:
        callback = self.callback.pop(0)

      # No callback
      except IndexError:
        return self

      try:
        result = self.next(callback)

        self.next = lambda callback: callback(result)

      #except as self.data:
      except:
        self.next = lambda callback: callback.throw(sys.exc_info()[1])

  def __call__(self, *args, **kwds):

    # Already triggered
    if hasattr(self, 'next'):
      raise StopIteration

    self.next = lambda callback: callback(*args, **kwds)
    self.propagate()

    return self

  def connect(self, callback):
    self.callback.append(callback)

    # Already triggered
    if hasattr(self, 'next'):
      self.propagate()

    return self

  def __init__(self):
    self.callback = []

  def throw(self, e):

    # Already triggered
    if hasattr(self, 'next'):
      raise StopIteration

    self.next = lambda callback: callback.throw(e)
    self.propagate()

    return self

# Sequence is a callback.  An advantage is that it can replace a function or
# callback without maintaining two references, one to .push() and one to the
# sequence
class Sequence:
  def __call__(self, *args, **kwds):
    try:
      item = self.consume.pop(0)

    except IndexError:
      item = Event()
      self.produce.append(item)

    item(*args, **kwds)

    return self

  def __init__(self):
    self.consume = []
    self.produce = []

  def shift(self):
    try:
      return self.produce.pop(0)

    except IndexError:
      item = Event()
      self.consume.append(item)

      return item

def connect(decorated):
  def wrapper(*args, **kwds):
    generator = decorated(*args, **kwds)

    # TODO Tail call elimination
    class Callback:
      def __call__(self, *args):
        try:
          return generator.send(args).connect(self)

        except StopIteration as e:
          try:
            return e.args[0]

          except IndexError:
            pass

      def throw(self, e):
        try:
          return generator.throw(e).connect(self)

        except StopIteration as e:
          try:
            return e.args[0]

          except IndexError:
            pass

    try:
      return generator.next().connect(Callback())

    except StopIteration as e:
      try:
        return e.args[0]

      except IndexError:
        pass

  return functools.update_wrapper(wrapper, decorated)
