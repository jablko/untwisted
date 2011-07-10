import untwisted

class connect:
  def __init__(ctx, *args, **kwds):
    try:
      module = kwds['module']

    except KeyError:
      import MySQLdb as module

    ctx.connect = untwisted.compose(untwisted.partial(setattr, ctx, 'conn'), untwisted.partial(module.connect, *args, **kwds))
    ctx.connect()

  def cursor(ctx):
    try:
      return ctx.conn.cursor()

    except:
      ctx.connect()

      return ctx.conn.cursor()
