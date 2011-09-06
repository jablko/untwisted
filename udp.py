import untwisted
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

      def makeConnection(ctx, transport):
        transport.connect(host, port)

    @untwisted.partial(setattr, ctx, '__call__')
    def _():

      # Avoid socket.bind()
      port = udp.Port(None, protocol)
      port.socket = port.createInternetSocket()
      port._connectToProtocol()

      return promise.promise()(port)
