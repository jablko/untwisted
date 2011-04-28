from twisted.internet import tcp
from untwisted import event

class Connect:
  def __init__(ctx, host, port, timeout=30, bindAddress=None):
    ctx.transport = event.Sequence()

    class Factory:
      class protocol:
        makeConnection = ctx.transport

        def __init__(ctx):
          ctx.dataReceived = event.Sequence()

    factory = Factory()

    ctx.connector = tcp.Connector(host, port, factory, timeout, bindAddress)

  def __call__(ctx):
    ctx.connector.connect()

    return ctx.transport.shift()

class Listen:
  def __init__(ctx, port, interface=None):
    ctx.transport = event.Sequence()

    class Factory:
      class protocol:
        makeConnection = ctx.transport

        def __init__(ctx):
          ctx.dataReceived = event.Sequence()

    factory = Factory()

    ctx.port = tcp.Port(port, factory, interface=interface)
    ctx.port.startListening()

  def __call__(ctx):
    return ctx.transport.shift()
