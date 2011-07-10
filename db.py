import untwisted

class connect:
  def __init__(ctx, *args, **kwds):
    try:
      module = kwds['module']

    except KeyError:
      import MySQLdb as module

    ctx.connect = untwisted.partial(module.connect, *args, **kwds)
    ctx.conn = ctx.connect()

  def cursor(ctx):
    try:
      return ctx.conn.cursor()

    except:
      ctx.conn = ctx.connect()

      return ctx.conn.cursor()
