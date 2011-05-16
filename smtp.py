import re, socket, untwisted
from untwisted import event, rfc5321

# Cache our domain
domain = socket.getfqdn()

class reply:
  def __init__(ctx, code, *args):
    ctx.code = code
    ctx.text = args if len(args) else {
      221: ('Service closing transmission channel',),
      250: ('Requested mail action okay, completed',),
      354: ('Start mail input; end with <CRLF>.<CRLF>',),
      500: ('Syntax error, command unrecognized',),
      502: ('Command not implemented',),
      503: ('Bad sequence of commands',),
      555: ('MAIL FROM/RCPT TO parameters not recognized or not implemented',)}[code]

  __int__ = lambda ctx: ctx.code

  __str__ = lambda ctx: ''.join(str(ctx.code) + '-' + text + '\r\n' for text in ctx.text[:-1]) + str(ctx.code) + ' ' + ctx.text[-1] + '\r\n'

class command:
  def __init__(ctx, verb, *args):
    ctx.verb = verb

    try:
      ctx.verb, ctx.text = verb.split(' ', 1)

    except ValueError:
      pass

    try:
      ctx.text, = args

    except ValueError:
      pass

  def __str__(ctx):
    str = ctx.verb

    try:
      str += ' ' + ctx.text

    except AttributeError:
      pass

    return str + '\r\n'

class client:

  # Since some servers may generate other replies under special circumstances,
  # and to allow for future extension, SMTP clients SHOULD, when possible,
  # interpret only the first digit of the reply and MUST be prepared to deal
  # with unrecognized reply codes by interpreting the first digit only

  @event.continuate
  def reply(ctx, expect=range(200, 300)):
    read = ''
    while True:
      read += yield ctx.transport.protocol.dataReceived.shift()

      match = re.match(rfc5321.replyLine, read)
      if match:
        break

    # TODO Extract multiple textstring, regex currently supports only last one
    reply = reply(match.group(1), match.group(2))

    if int(reply) not in expect:
      raise reply

    #return ...
    raise StopIteration(reply)

  def ehlo(ctx):
    ctx.transport.write(str(command('EHLO', domain)))

    return ctx.reply()

  def helo(ctx):
    ctx.transport.write(str(command('HELO', domain)))

    return ctx.reply()

  class mail:
    class __metaclass__(type):
      __get__ = untwisted.ctxual

    def mail(ctx, mailbox):
      #ctx.ctx.transport.write(str(command('MAIL FROM:<{}>'.format(mailbox))))
      ctx.ctx.transport.write(str(command('MAIL FROM:<{0}>'.format(mailbox))))

      return ctx.ctx.reply()

    def mail(ctx):
      raise NotImplementedError

    def rcpt(ctx, mailbox):
      #ctx.ctx.transport.write(str(command('RCPT TO:<{}>'.format(mailbox))))
      ctx.ctx.transport.write(str(command('RCPT TO:<{0}>'.format(mailbox))))

      return ctx.ctx.reply()

    def recipient(ctx):
      raise NotImplementedError

    @event.continuate
    def data(ctx, data):
      ctx.ctx.trasport.write(str(command('DATA')))

      # Since some servers may generate other replies under special
      # circumstances, and to allow for future extension, SMTP clients SHOULD,
      # when possible, interpret only the first digit of the reply and MUST be
      # prepared to deal with unrecognized reply codes by interpreting the
      # first digit only
      yield ctx.ctx.reply(range(300, 400))

      # Before sending a line of mail text, the SMTP client checks the first
      # character of the line.  If it is a period, one additional period is
      # inserted at the beginning of the line

      # Lookbehind requires fixed width pattern
      ctx.ctx.transport.write(re.sub('(^|\r\n)\.', '\\1..', data))

      #return ...
      raise StopIteration(ctx.ctx.reply())

    def data(ctx):
      raise NotImplementedError

    def __init__(ctx):

      @untwisted.call
      @event.continuate
      def ignore():
        yield ctx.mail()

        yield ctx.recipient()

        try:
          while True:
            yield ctx.recipient()

        except StopIteration:
          yield ctx.data()

  def __init__(ctx, transport):
    ctx.transport = transport

    @untwisted.call
    @event.continuate
    def ignore():
      yield ctx.reply()

      try:
        yield ctx.ehlo()

      except reply as e:
        if int(e) not in (500, 502):
          raise

        yield ctx.helo()

      try:
        while True:
          yield ctx.mail()

      except StopIteration:
        pass

class server:
  greeting = lambda ctx: ctx.transport.write(str(reply(220, domain)))

  @event.continuate
  def command(ctx):
    read = ''
    while True:
      read += yield ctx.transport.protocol.dataReceived.shift()
      try:
        index = read.index('\r\n')

        break

      except ValueError:
        pass

    # TODO Raise if index not end?
    #return ...
    raise StopIteration(command(read[:index]))

  @event.continuate
  def start(ctx, command, state):
    if 'EHLO' == command.verb:
      ctx.transport.write(str(reply(250, domain)))

      #return ...
      raise StopIteration(ctx.mail())

    if 'HELO' == command.verb:

      # Servers MUST NOT return the extended EHLO-style response to a HELO
      # command
      ctx.transport.write(str(reply(250, domain)))

      #return ...
      raise StopIteration(ctx.mail())

    if command.verb in ('MAIL', 'RCPT', 'DATA'):
      ctx.transport.write(str(reply(503)))

      #return ...
      raise StopIteration(state((yield ctx.command()), state))

    if command.verb in ('RSET', 'NOOP'):
      ctx.transport.write(str(reply(250)))

      #return ...
      raise StopIteration(state((yield ctx.command()), state))

    if command.verb in ('VRFY', 'EXPN', 'HELP'):
      ctx.transport.write(str(reply(502)))

      #return ...
      raise StopIteration(state((yield ctx.command()), state))

    if 'QUIT' == command.verb:
      #return ...
      raise StopIteration(ctx.transport.write(str(reply(221))))

    # TODO Log?
    ctx.transport.write(str(reply(500)))

    state((yield ctx.command()), state)

  class mail:
    class __metaclass__(type):
      __get__ = untwisted.ctxual

    def mail(ctx, mailbox):
      raise NotImplementedError

    @event.continuate
    def start(ctx, command, state):

      # MAIL (or SEND, SOML, or SAML) MUST NOT be sent if a mail transaction is
      # already open, i.e., it should be sent only if no mail transaction had
      # been started in the session, or if the previous one successfully
      # concluded with a successful DATA command, or if the previous one was
      # aborted, e.g., with a RSET or new EHLO
      if 'MAIL' == command.verb:
        match = re.match(rfc5321.mail, command)
        try:
          if not match:
            raise reply(555)

          try:
            yield ctx.mail(match.group(1))

          # TODO Log
          except NotImplementedError:
            raise reply(502)

          raise reply(250)

        except reply as e:
          ctx.ctx.transport.write(str(e))

          if int(e) in range(200, 300):
            #return ...
            raise StopIteration(ctx.afterMail((yield ctx.ctx.command()), ctx.afterMail))

          #return ...
          raise StopIteration(state((yield ctx.ctx.command()), state))

      if 'RSET' == command.verb:
        ctx.ctx.transport.write(str(reply(250)))

        #return ...
        raise StopIteration(ctx.ctx.mail())

      #return ...
      raise StopIteration(ctx.ctx.start(command, state))

    def recipient(ctx, mailbox):
      raise NotImplementedError

    @event.continuate
    def afterMail(ctx, command, state):

      # Once started, a mail transaction consists of a transaction beginning
      # command, one or more RCPT commands, and a DATA command, in that order
      if 'RCPT' == command.verb:
        match = re.match(rfc5321.rcpt, command)
        try:
          if not match:
            raise reply(555)

          try:
            yield ctx.recipient(match.group(1))

          # TODO Log
          except NotImplementedError:
            raise reply(502)

          raise reply(250)

        except reply as e:
          ctx.ctx.transport.write(str(e))

          if int(e) in range(200, 300):
            #return ...
            raise StopIteration(ctx.afterRecipient((yield ctx.ctx.command()), ctx.afterRecipient))

          #return ...
          raise StopIteration(state((yield ctx.ctx.command()), state))

      if 'RSET' == command.verb:
        ctx.ctx.transport.write(str(reply(250)))

        #return ...
        raise StopIteration(ctx.ctx.mail())

      #return ...
      raise StopIteration(ctx.ctx.start(command, state))

    def data(ctx, data):
      raise NotImplementedError

    @event.continuate
    def afterRecipient(ctx, command, state):
      if 'DATA' == command.verb:
        ctx.ctx.transport.write(str(reply(354)))

        read = ''
        while True:
          read += yield ctx.ctx.transport.protocol.dataReceived.shift()
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
            yield ctx.data(re.sub('(^|\r\n)\.(?=.)', '\\1', read[:index]))

          # TODO Log
          except NotImplementedError:
            raise reply(502)

          raise reply(250)

        except reply as e:
          ctx.ctx.transport.write(str(e))

          if int(e) in range(200, 300):
            #return ...
            raise StopIteration(ctx.ctx.mail())

          #return ...
          raise StopIteration(state((yield ctx.ctx.command()), state))

      #return ...
      raise StopIteration(ctx.afterMail(command, state))

    def __init__(ctx):
      event.continuate(lambda: ctx.start((yield ctx.ctx.command()), ctx.start))()

  def __init__(ctx, transport):
    ctx.transport = transport

    ctx.greeting()

    event.continuate(lambda: ctx.start((yield ctx.command()), ctx.start))()
