import socket, untwisted
from twisted.internet import protocol, reactor, tcp
from untwisted import promise

def connect(host, port, timeout=30, bindAddress=None):

  # Avoid TypeError: Error when calling the metaclass bases, a new-style class
  # can't have only classic bases
  class result(tcp.Connector, object):
    class __metaclass__(type):
      def __call__(ctx):
        transport = promise.promise()

        # Extend protocol.ClientFactory for .startedConnecting()

        @untwisted.call
        class factory(protocol.ClientFactory):
          class protocol:
            def __init__(ctx):
              ctx.connectionLost = promise.promise()

              ctx.dataReceived = promise.sequence()

              # .dataReceived() must return falsy: SelectReactor._doReadOrWrite()

              __call__ = ctx.dataReceived.__call__

              @untwisted.partial(setattr, ctx.dataReceived, '__call__')
              def _(*args, **kwds):
                __call__(*args, **kwds)

            makeConnection = transport

        type.__call__(ctx, host, port, factory, timeout, bindAddress, reactor).connect()

        return transport

    class _makeTransport(tcp.Client):
      class __metaclass__(type):
        __call__ = lambda ctx: type.__call__(ctx, ctx.ctx.host, ctx.ctx.port, ctx.ctx.bindAddress, ctx.ctx, ctx.ctx.reactor)
        __get__ = untwisted.ctxual

      def close(ctx):
        ctx.loseConnection()

        return ctx.protocol.connectionLost

  return result

def listen(port, interface=''):
  transport = promise.sequence()

  # Extend protocol.Factory for .doStart()

  @untwisted.call
  class factory(protocol.Factory):
    class protocol:
      def __init__(ctx):
        ctx.connectionLost = promise.promise()

        ctx.dataReceived = promise.sequence()

        # .dataReceived() must return falsy: SelectReactor._doReadOrWrite()

        __call__ = ctx.dataReceived.__call__

        @untwisted.partial(setattr, ctx.dataReceived, '__call__')
        def _(*args, **kwds):
          __call__(*args, **kwds)

      makeConnection = transport

  @untwisted.call
  class _(tcp.Port):
    class __metaclass__(type):
      def __call__(ctx):
        try:
          type.__call__(ctx, port, factory, interface=interface).startListening()

        # tcp.Connector calls socket.getservbyname() but tcp.Port doesn't : (
        except TypeError:
          nstPort = socket.getservbyname(port, 'tcp')

          type.__call__(ctx, nstPort, factory, interface=interface).startListening()

    class transport(tcp.Server):
      def close(ctx):
        ctx.loseConnection()

        return ctx.protocol.connectionLost

  return transport.shift
