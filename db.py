import untwisted

class connect:
  def __init__(ctx, *args, **kwds):
    try:
      module = kwds['module']

    except KeyError:
      import MySQLdb as module

    ctx.connect = lambda: (ctx, setattr(ctx, 'conn', module.connect(*args, **kwds)))[0]
    ctx.connect()

  def cursor(ctx):
    try:
      return ctx.conn.cursor()

    except:
      return ctx.connect().conn.cursor()
