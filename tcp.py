import untwisted
from twisted.internet import protocol, reactor, tcp
from untwisted import promise

class connect:
  def __init__(ctx, host, port, timeout=30, bindAddress=None):
    ctx.transport = promise.sequence()

    # Extend protocol.ClientFactory for .startedConnecting()

    @untwisted.call
    class factory(protocol.ClientFactory):

      # Extend protocol.Protocol for .connectionLost()
      class protocol(protocol.Protocol):
        makeConnection = ctx.transport

        def __init__(ctx):
          ctx.dataReceived = promise.sequence()

    ctx.connector = tcp.Connector(host, port, factory, timeout, bindAddress, reactor)

  def __call__(ctx):
    ctx.connector.connect()

    return ctx.transport.shift()

class listen:
  def __init__(ctx, port, interface=''):
    ctx.transport = promise.sequence()

    # Extend protocol.Factory for .doStart()

    @untwisted.call
    class factory(protocol.Factory):

      # Extend protocol.Protocol for .connectionLost()
      class protocol(protocol.Protocol):
        makeConnection = ctx.transport

        def __init__(ctx):
          ctx.dataReceived = promise.sequence()

    ctx.port = tcp.Port(port, factory, interface=interface)
    ctx.port.startListening()

  def __call__(ctx):
    return ctx.transport.shift()
