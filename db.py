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

    close = lambda ctx: (ctx, ctx.cursor.close())[0]

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

    fetchone = lambda ctx: ctx.cursor.fetchone()
