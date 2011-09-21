import untwisted

class connect:
  def __init__(ctx, *args, **kwds):
    try:
      module = kwds['module']
      del kwds['module']

    except KeyError:
      import MySQLdb as module

    ctx.connect = lambda: (ctx, setattr(ctx, 'conn', module.connect(*args, **kwds)))[0]
    ctx.connect()

    ctx.module = module

  class cursor:
    class __metaclass__(type):
      __get__ = untwisted.ctxual

    def __init__(ctx):
      ctx.cursor = ctx.ctx.conn.cursor()

    def close(ctx):
      ctx.cursor.close()

      return ctx

    def execute(ctx, operation, *args):
      try:
        args, = args

      except ValueError:
        pass

      try:
        ctx.cursor.execute(operation, args)

      except ctx.ctx.module.OperationalError:
        ctx.cursor = ctx.ctx.connect().conn.cursor()
        ctx.cursor.execute(operation, args)

      return ctx

    def executemany(ctx, operation, *args):
      try:
        ctx.cursor.executemany(operation, args)

      except ctx.ctx.module.OperationalError:
        ctx.cursor = ctx.ctx.connect().conn.cursor()
        ctx.cursor.executemany(operation, args)

      return ctx

    __iter__ = untwisted.identity

    def next(ctx):
      result = ctx.cursor.fetchone()
      if result:
        return result

      raise StopIteration

  def __iter__(ctx):
    cursor = ctx.cursor()

    try:
      yield cursor

    finally:
      cursor.close()
