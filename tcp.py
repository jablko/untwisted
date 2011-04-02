from twisted.internet import tcp
from untwisted import event

class Connect:
  def __init__(self, host, port, timeout=30, bindAddress=None):
    self.transport = event.Sequence()

    class Factory:
      class protocol:
        makeConnection = self.transport

        def __init__(self):
          self.dataReceived = event.Sequence()

    factory = Factory()

    self.connector = tcp.Connector(host, port, factory, timeout, bindAddress)

  def __call__(self):
    self.connector.connect()

    return self.transport.shift()

class Listen:
  def __init__(self, port, interface=None):
    self.transport = event.Sequence()

    class Factory:
      class protocol:
        makeConnection = self.transport

        def __init__(self):
          self.dataReceived = event.Sequence()

    factory = Factory()

    self.port = tcp.Port(port, factory, interface=interface)
    self.port.startListening()

  def __call__(self):
    return self.transport.shift()
