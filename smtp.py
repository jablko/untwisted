import re, socket
from untwisted import event

# Cache our domain
domain = socket.getfqdn()

class Reply:
  def __init__(self, code, *args):
    self.code = code

    try:
      self.text, = args

    except ValueError:
      self.text = {
        221: ['Service closing transmission channel'],
        250: ['Requested mail action okay, completed'],
        354: ['Start mail input; end with <CRLF>.<CRLF>'],
        500: ['Syntax error, command unrecognized'],
        502: ['Command not implemented'],
        503: ['Bad sequence of commands'],
        555: ['MAIL FROM/RCPT TO parameters not recognized or not implemented']}[code]

  def __int__(self):
    return self.code

  def __str__(self):
    return ''.join([str(self.code) + '-' + text + '\r\n' for text in self.text[0:-1]]) + str(self.code) + ' ' + self.text[-1] + '\r\n'

class Command:
  def __init__(self, verb, *args):
    self.verb = verb

    try:
      self.verb, self.text = verb.split(' ', 1)

    except ValueError:
      pass

    try:
      self.text, = args

    except ValueError:
      pass

  def __str__(self):
    str = self.verb

    try:
      str += ' ' + self.text

    except AttributeError:
      pass

    return str + '\r\n'

class Client:

  # Since some servers may generate other replies under special circumstances,
  # and to allow for future extension, SMTP clients SHOULD, when possible,
  # interpret only the first digit of the reply and MUST be prepared to deal
  # with unrecognized reply codes by interpreting the first digit only

  @event.connect
  def reply(self, expect=range(200, 300)):
    read = ''
    while True:
      read += yield self.transport.protocol.dataReceived.shift()

      match = re.match(rfc5321.replyLine, read)
      if match:
        break

    # TODO Extract multiple textstring, regex currently supports only last one
    reply = Reply(match.group(1), [match.group(2)])

    if int(reply) not in expect:
      raise reply

    #return reply
    raise StopIteration(reply)

  def ehlo(self):
    self.transport.write(Command('EHLO', domain))

    return self.reply()

  def helo(self):
    self.transport.write(Command('HELO', domain))

    return self.reply()

  class Mail:
    def mail(self, mailbox):
      self.client.transport.write(Command('MAIL FROM:<%s>' % mailbox))

      return self.client.reply()

    def mail(self):
      raise NotImplementedError

    def rcpt(self, mailbox):
      self.client.transport.write(Command('RCPT TO:<%s>' % mailbox))

      return self.client.reply()

    def recipient(self):
      raise NotImplementedError

    @event.connect
    def data(self, data):

      self.client.trasport.write(Command('DATA'))

      # Since some servers may generate other replies under special
      # circumstances, and to allow for future extension, SMTP clients SHOULD,
      # when possible, interpret only the first digit of the reply and MUST be
      # prepared to deal with unrecognized reply codes by interpreting the
      # first digit only
      yield self.client.reply(range(300, 400))

      # Before sending a line of mail text, the SMTP client checks the first
      # character of the line.  If it is a period, one additional period is
      # inserted at the beginning of the line

      # Lookbehind requires fixed width pattern
      self.client.transport.write(re.sub('(^|\r\n)\.', '\\1..', data))

      #return self.client.reply()
      raise StopIteration(self.client.reply())

    def data(self):
      raise NotImplementedError

    def __init__(self, client):
      self.client = client

      yield self.mail()

      yield self.recipient()

      try:
        while True:
          yield self.recipient()

      except StopIteration:
        yield self.data()

  def __init__(self, transport):
    self.transport = transport

    yield self.reply()

    try:
      yield self.ehlo()

    except Reply as e:
      if int(e) not in (500, 502):
        raise

      yield self.helo()

    try:
      while True:
        yield self.Mail(self)

    except StopIteration:
      pass

class Server:
  def greeting(self):
    self.transport.write(Reply(220, [domain]))

  @event.connect
  def command(self):
    read = ''
    while True:
      read += yield self.transport.protocol.dataReceived.shift()
      try:
        index = read.index('\r\n')

        break

      except ValueError:
        pass

    # TODO Raise if index not end?
    #return Command(read[:index])
    raise StopIteration(Command(read[:index]))

  @event.connect
  def start(self, command, state):
    if 'EHLO' == command.verb:
      self.transport.write(Reply(250, [domain]))

      #return self.Mail(self)
      raise StopIteration(self.Mail(self))

    if 'HELO' == command.verb:

      # Servers MUST NOT return the extended EHLO-style response to a HELO
      # command
      self.transport.write(Reply(250, [domain]))

      #return self.Mail(self)
      raise StopIteration(self.Mail(self))

    if command.verb in ('MAIL', 'RCPT', 'DATA'):
      self.transport.write(Reply(503))

      #return state((yield self.command()), state)
      raise StopIteration(state((yield self.command()), state))

    if command.verb in ('RSET', 'NOOP'):
      self.transport.write(Reply(250))

      #return state((yield self.command()), state)
      raise StopIteration(state((yield self.command()), state))

    if command.verb in ('VRFY', 'EXPN', 'HELP'):
      self.transport.write(Reply(502))

      #return state((yield self.command()), state)
      raise StopIteration(state((yield self.server.command()), state))

    if 'QUIT' == command.verb:
      #return self.transport.write(Reply(221))
      raise StopIteration(self.transport.write(Reply(221)))

    # TODO Log?
    self.transport.write(Reply(500))

    state((yield self.server.command()), state)

  class Mail:
    def mail(self, mailbox):
      raise NotImplementedError

    @event.connect
    def start(self, command, state):

      # MAIL (or SEND, SOML, or SAML) MUST NOT be sent if a mail transaction is
      # already open, i.e., it should be sent only if no mail transaction had
      # been started in the session, or if the previous one successfully
      # concluded with a successful DATA command, or if the previous one was
      # aborted, e.g., with a RSET or new EHLO
      if 'MAIL' == command.verb:
        match = re.match(rfc5321.mail, command)
        try:
          if not match:
            raise Reply(555)

          try:
            yield self.mail(match.group(1))

          # TODO Log
          except NotImplementedError:
            raise Reply(502)

          raise Reply(250)

        except Reply as e:
          self.server.transport.write(e)

          if int(e) in range(200, 300):
            #return self.afterMail((yield self.server.command()), self.afterMail)
            raise StopIteration(self.afterMail((yield self.server.command()), self.afterMail))

          #return state((yield self.server.command()), state)
          raise StopIteration(state((yield self.server.command()), state))

      if 'RSET' == command.verb:
        self.server.transport.write(Reply(250))

        #return self.server.Mail(self.server)
        raise StopIteration(self.server.Mail(self.server))

      #return self.server.start(command, state)
      raise StopIteration(self.server.start(command, state))

    def recipient(self, mailbox):
      raise NotImplementedError

    @event.connect
    def afterMail(self, command, state):

      # Once started, a mail transaction consists of a transaction beginning
      # command, one or more RCPT commands, and a DATA command, in that order
      if 'RCPT' == command.verb:
        match = re.match(rfc5321.rcpt, command)
        try:
          if not match:
            raise Reply(555)

          try:
            yield self.recipient(match.group(1))

          # TODO Log
          except NotImplementedError:
            raise Reply(502)

          raise Reply(250)

        except Reply as e:
          self.server.transport.write(e)

          if int(e) in range(200, 300):
            #return self.afterRecipient((yield self.server.command()), self.afterRecipient)
            raise StopIteration(self.afterRecipient((yield self.server.command()), self.afterRecipient))

          #return state((yield self.server.command()), state)
          raise StopIteration(state((yield self.server.command()), state))

      if 'RSET' == command.verb:
        self.server.transport.write(Reply(250))

        #return self.server.Mail(self.server)
        raise StopIteration(self.server.Mail(self.server))

      #return self.server.start(command, state)
      raise StopIteration(self.server.start(command, state))

    def data(self, data):
      raise NotImplementedError

    @event.connect
    def afterRecipient(self, command, state):
      if 'DATA' == command.verb:
        self.server.transport.write(Reply(354))

        read = ''
        while True:
          read += yield self.server.transport.protocol.dataReceived.shift()
          try:
            index = read.index('\r\n.\r\n')

            break

          except ValueError:
            pass

        # TODO Raise if index not end?

        try:
          try:

            # When a line of mail text is received by the SMTP server, it
            # checks the line.  If the line is composed of a single period, it
            # is treated as the end of mail indicator.  If the first character
            # is a period and there are other characters on the line, the first
            # character is deleted

            # Lookbehind requires fixed width pattern
            yield self.data(re.sub('(^|\r\n)\.(?=.)', '\\1', read[:index]))

          # TODO Log
          except NotImplementedError:
            raise Reply(502)

          raise Reply(250)

        except Reply as e:
          self.server.transport.write(e)

          if int(e) in range(200, 300):
            #return self.server.Mail(self.server)
            raise StopIteration(self.server.Mail(self.server))

          #return state((yield self.server.command()), state)
          raise StopIteration(state((yield self.server.command()), state))

      #return self.afterMail(command, state)
      raise StopIteration(self.afterMail(command, state))

    def __init__(self, server):
      self.start((yield server.command()), self.start)

  def __init__(self, transport):
    self.transport = transport

    self.greeting()

    self.start((yield self.command()), self.start)
