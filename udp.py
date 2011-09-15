import socket, untwisted
from twisted.internet import udp
from untwisted import promise

# A connected UDP socket is slightly different from a standard one - it can
# only send and receive datagrams to/from a single address, but this does not
# in any way imply a connection.  Datagrams may still arrive in any order, and
# the port on the other side may have no one listening,
# http://twistedmatrix.com/documents/current/core/howto/udp.html#auto2
def connect(host, port):
  transport = promise.sequence()

  @untwisted.call
  class protocol:
    datagramReceived = promise.sequence()

    # Avoid AttributeError: protocol instance has no attribute 'doStop'
    def doStop(ctx):
      pass

    @promise.resume
    def makeConnection(ctx, nstTransport):
      nstHost = host

      try:
        try:
          nstTransport.connect(host, port)

        except ValueError:

          # Avoid ImportError: cannot import name dns
          from untwisted import dns

          nstHost = (yield dns.lookup(host)).answer[0].address

          nstTransport.connect(nstHost, port)

      # tcp.Connector calls socket.getservbyname() but .connect() doesn't : (
      except TypeError:
        nstPort = socket.getservbyname(port, 'udp')

        # Fix RuntimeError: already connected
        nstTransport._connectedAddr = None

        nstTransport.connect(nstHost, nstPort)

      nstTransport.recv = untwisted.compose(untwisted.partial(promise.promise.then, callback=lambda asdf, _: asdf), ctx.datagramReceived.shift)

      transport(nstTransport)

  def result():

    # Avoid socket.bind()
    port = udp.Port(None, protocol)

    port.socket = port.createInternetSocket()
    port.fileno = port.socket.fileno

    port._connectToProtocol()

    return transport.shift()

  return result
