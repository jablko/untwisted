import socket, untwisted
from twisted.internet import protocol, reactor, tcp
from untwisted import promise

def connect(host, port, timeout=30, bindAddress=None):
  transport = promise.sequence()

  # Extend protocol.ClientFactory for .startedConnecting()

  @untwisted.call
  class factory(protocol.ClientFactory):

    # Extend protocol.Protocol for .connectionLost()
    class protocol(protocol.Protocol):
      def __init__(ctx):
        ctx.connectionLost = promise.promise()

        ctx.dataReceived = promise.sequence()

        # .dataReceived() must return falsy: SelectReactor._doReadOrWrite()

        __call__ = ctx.dataReceived.__call__

        @untwisted.partial(setattr, ctx.dataReceived, '__call__')
        def _(*args, **kwds):
          __call__(*args, **kwds)

      def makeConnection(ctx, nstTransport):

        @untwisted.partial(setattr, nstTransport, 'close')
        def _():
          nstTransport.loseConnection()

          return ctx.connectionLost

        transport(nstTransport)

  def result():
    tcp.Connector(host, port, factory, timeout, bindAddress, reactor).connect()

    return transport.shift()

  return result

def listen(port, interface=''):
  transport = promise.sequence()

  # Extend protocol.Factory for .doStart()

  @untwisted.call
  class factory(protocol.Factory):

    # Extend protocol.Protocol for .connectionLost()
    class protocol(protocol.Protocol):
      def __init__(ctx):
        ctx.connectionLost = promise.promise()

        ctx.dataReceived = promise.sequence()

        # .dataReceived() must return falsy: SelectReactor._doReadOrWrite()

        __call__ = ctx.dataReceived.__call__

        @untwisted.partial(setattr, ctx.dataReceived, '__call__')
        def _(*args, **kwds):
          __call__(*args, **kwds)

      def makeConnection(ctx, nstTransport):

        @untwisted.partial(setattr, nstTransport, 'close')
        def _():
          nstTransport.loseConnection()

          return ctx.connectionLost

        transport(nstTransport)

  try:
    tcp.Port(port, factory, interface=interface).startListening()

  # tcp.Connector calls socket.getservbyname() but tcp.Port doesn't : (
  except TypeError:
    port = socket.getservbyname(port, 'tcp')

    tcp.Port(port, factory, interface=interface).startListening()

  return transport.shift
