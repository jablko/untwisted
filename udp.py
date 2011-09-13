import socket, untwisted
from twisted.internet import udp
from untwisted import promise

# A connected UDP socket is slightly different from a standard one - it can
# only send and receive datagrams to/from a single address, but this does not
# in any way imply a connection.  Datagrams may still arrive in any order, and
# the port on the other side may have no one listening,
# http://twistedmatrix.com/documents/current/core/howto/udp.html#auto2
class connect:
  def __init__(ctx, host, port):

    @untwisted.call
    class protocol:
      datagramReceived = promise.sequence()

      # Avoid AttributeError: protocol instance has no attribute 'doStop'
      def doStop(ctx):
        pass

      def makeConnection(ctx, transport):
        try:
          transport.connect(host, port)

        # tcp.Connector calls socket.getservbyname() but .connect() doesn't : (
        except TypeError:

          # Fix RuntimeError: already connected
          transport._connectedAddr = None

          transport.connect(host, socket.getservbyname(port, 'udp'))

        transport.recv = untwisted.compose(untwisted.partial(promise.promise.then, callback=lambda asdf, _: asdf), ctx.datagramReceived.shift)

    @untwisted.partial(setattr, ctx, '__call__')
    def _():

      # Avoid socket.bind()
      port = udp.Port(None, protocol)

      port.socket = port.createInternetSocket()
      port.fileno = port.socket.fileno

      port._connectToProtocol()

      return promise.promise()(port)
