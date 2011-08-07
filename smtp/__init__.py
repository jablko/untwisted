import re, socket, untwisted
from untwisted import promise, rfc5321

# Cache our domain
domain = socket.getfqdn()

class command:
  def __init__(ctx, verb, *args):
    ctx.verb = verb

    try:
      ctx.text, = args

    except ValueError:
      try:
        ctx.verb, ctx.text = verb.split(' ', 1)

      except ValueError:
        pass

  def __str__(ctx):
    result = ctx.verb

    try:
      result += ' ' + ctx.text

    except AttributeError:
      pass

    return result + '\r\n'

class reply:
  def __init__(ctx, code, *args):
    ctx.code = code

    try:
      ctx.text = args or {
        221: ('Service closing transmission channel',),
        250: ('Requested mail action okay, completed',),
        354: ('Start mail input; end with <CRLF>.<CRLF>',),
        500: ('Syntax error, command unrecognized',),
        502: ('Command not implemented',),
        503: ('Bad sequence of commands',),
        555: ('MAIL FROM/RCPT TO parameters not recognized or not implemented',)}[code]

    except KeyError:
      pass

  __int__ = lambda ctx: ctx.code

  def __str__(ctx):
    result = str(ctx.code)

    try:
      result += ' ' + ctx.text[-1]

    except AttributeError:
      pass

    else:
      result = ''.join(str(ctx.code) + '-' + text + '\r\n' for text in ctx.text[:-1]) + result

    return result + '\r\n'

class client:
  class __metaclass__(type):

    @promise.continuate
    def __call__(ctx, transport):
      ctx = type.__call__(ctx, transport)

      # Greeting
      yield ctx.reply()

      try:
        yield ctx.ehlo()

      except reply as e:
        if int(e) not in (500, 502):
          raise

        yield ctx.helo()

      while True:
        try:
          yield ctx.mail()

        except StopIteration:
          break

      #return ...
      raise StopIteration(ctx.quit())

  read = ''

  def __init__(ctx, transport):
    ctx.transport = transport

  head = promise.promise()(None)

  # Since some servers may generate other replies under special circumstances,
  # and to allow for future extension, SMTP clients SHOULD, when possible,
  # interpret only the first digit of the reply and MUST be prepared to deal
  # with unrecognized reply codes by interpreting the first digit only
  def reply(ctx, expect=range(200, 300)):
    prev = ctx.head
    ctx.head = promise.promise()

    prev.then(ctx.head.then(promise.promise()))

    @ctx.head.then
    @promise.continuate
    def _(clone):
      try:
        prev.traceback = clone.traceback

      except AttributeError:
        pass

      prev.args = clone.args
      prev.kwds = clone.kwds

      while True:
        try:
          replyLine = rfc5321.replyLine.match(ctx.read, '( replyCode, textstring )')

          break

        except ValueError:
          ctx.read += yield ctx.transport.protocol.dataReceived.shift()

      ctx.read = ctx.read[len(replyLine):]

      yield clone

      result = reply(int(replyLine.replyCode), *map(str, replyLine.textstring))
      if int(result) not in expect:
        raise result

      #return ...
      raise StopIteration(result)

    return ctx.head

  def ehlo(ctx):
    ctx.transport.write(str(command('EHLO', domain)))

    return ctx.reply()

  def helo(ctx):
    ctx.transport.write(str(command('HELO', domain)))

    return ctx.reply()

  class mail:
    class __metaclass__(type):
      __get__ = untwisted.ctxual

      @promise.continuate
      def __call__(ctx):
        ctx = type.__call__(ctx)

        result = yield ctx.sender()
        if not isinstance(result, reply):
          yield ctx.mail(result)

        result = yield ctx.recipient()
        if not isinstance(result, reply):
          yield ctx.rcpt(result)

        while True:
          try:
            result = yield ctx.recipient()

          except StopIteration:
            break

          if not isinstance(result, reply):
            yield ctx.rcpt(result)

        result = yield ctx.content()
        if not isinstance(result, reply):
          #return ...
          raise StopIteration(ctx.data(result))

        #return ...
        raise StopIteration(result)

    def mail(ctx, sender):
      #ctx.ctx.transport.write(str(command('MAIL FROM:<{}>'.format(sender))))
      ctx.ctx.transport.write(str(command('MAIL FROM:<{0}>'.format(sender))))

      return ctx.ctx.reply()

    def sender(ctx):
      raise NotImplementedError

    def rcpt(ctx, recipient):
      #ctx.ctx.transport.write(str(command('RCPT TO:<{}>'.format(recipient))))
      ctx.ctx.transport.write(str(command('RCPT TO:<{0}>'.format(recipient))))

      return ctx.ctx.reply()

    def recipient(ctx):
      raise NotImplementedError

    @promise.continuate
    def data(ctx, content):
      ctx.ctx.transport.write(str(command('DATA')))

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
      content = re.sub('(^|\r\n)\.', '\\1..', content)

      # An extra <CRLF> MUST NOT be added, as that would cause an empty line to
      # be added to the message.  The only exception to this rule would arise
      # if the message body were passed to the originating SMTP-sender with a
      # final "line" that did not end in <CRLF>; in that case, the originating
      # SMTP system MUST either reject the message as invalid or add <CRLF> in
      # order to have the receiving SMTP server recognize the "end of data"
      # condition
      if '\r\n' != content[-2:]:
        content += '\r\n'

      content += '.\r\n'

      ctx.ctx.transport.write(content)

      #return ...
      raise StopIteration(ctx.ctx.reply())

    def content(ctx):
      raise NotImplementedError

  def rset(ctx):
    ctx.transport.write(str(command('RSET')))

    return ctx.reply()

  def quit(ctx):
    ctx.transport.write(str(command('QUIT')))

    return ctx.reply()

class pipeline(client):
  pipeline = False

  @promise.continuate
  def ehlo(ctx):
    result = yield client.ehlo(ctx)

    ctx.pipeline = 'PIPELINING' in result.text[1:]

    #return ...
    raise StopIteration(result)

  class mail(client.mail):
    def mail(ctx, sender):
      result = client.mail.mail(ctx, sender)
      if ctx.ctx.pipeline:
        result = promise.promise()(result)

      return result

    def rcpt(ctx, recipient):
      result = client.mail.rcpt(ctx, recipient)
      if ctx.ctx.pipeline:
        result = promise.promise()(result)

      return result

    @promise.continuate
    def data(ctx, content):
      ctx.ctx.transport.write(str(command('DATA')))

      yield ctx.ctx.reply(range(300, 400))

      content = re.sub('(^|\r\n)\.', '\\1..', content)

      if '\r\n' != content[-2:]:
        content += '\r\n'

      content += '.\r\n'

      ctx.ctx.transport.write(content)

      result = ctx.ctx.reply()
      if ctx.ctx.pipeline:
        result = promise.promise()(result)

      #return ...
      raise StopIteration(result)

  def rset(ctx):
    result = client.rset(ctx)
    if ctx.pipeline:
      result = promise.promise()(result)

    return result

class server:
  class __metaclass__(type):

    @promise.continuate
    def __call__(ctx, transport):
      ctx = type.__call__(ctx, transport)

      ctx.greeting()

      #return ...
      raise StopIteration(ctx.start((yield ctx.command()), ctx.start))

  read = ''

  def __init__(ctx, transport):
    ctx.transport = transport

  #greeting = lambda ctx: ctx.transport.write(str(reply(220, '{} Service ready'.format(domain))))
  greeting = lambda ctx: ctx.transport.write(str(reply(220, '{0} Service ready'.format(domain))))

  @promise.continuate
  def command(ctx):
    while True:
      try:
        result, ctx.read = ctx.read.split('\r\n', 1)

        break

      except ValueError:
        ctx.read += yield ctx.transport.protocol.dataReceived.shift()

    result = command(result)

    #return ...
    raise StopIteration(result)

  @promise.continuate
  def start(ctx, command, state):
    if 'EHLO' == command.verb:
      #ctx.transport.write(str(reply(250, '{} Requested mail action okay, completed'.format(domain), 'PIPELINING')))
      ctx.transport.write(str(reply(250, '{0} Requested mail action okay, completed'.format(domain), 'PIPELINING')))

      #return ...
      raise StopIteration(ctx.mail())

    if 'HELO' == command.verb:

      # Servers MUST NOT return the extended EHLO-style response to a HELO
      # command
      ctx.transport.write(str(reply(250)))

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
      ctx.transport.write(str(reply(221)))

      #return ...
      raise StopIteration(ctx.transport.loseConnection())

    # TODO Log?
    ctx.transport.write(str(reply(500)))

    state((yield ctx.command()), state)

  class mail:
    class __metaclass__(type):
      __get__ = untwisted.ctxual

      @promise.continuate
      def __call__(ctx):
        ctx = type.__call__(ctx)

        #return ...
        raise StopIteration(ctx.start((yield ctx.ctx.command()), ctx.start))

    def sender(ctx, sender):
      raise NotImplementedError

    @promise.continuate
    def start(ctx, command, state):

      # MAIL (or SEND, SOML, or SAML) MUST NOT be sent if a mail transaction is
      # already open, i.e., it should be sent only if no mail transaction had
      # been started in the session, or if the previous one successfully
      # concluded with a successful DATA command, or if the previous one was
      # aborted, e.g., with a RSET or new EHLO
      if 'MAIL' == command.verb:
        try:
          try:
            yield ctx.sender(rfc5321.mail.match(str(command), 'mailbox ( localPart, domain, addressLiteral )'))

          # TODO Log
          except NotImplementedError:
            raise reply(502)

          except ValueError:
            raise reply(555)

          raise reply(250)

        except reply as e:
          ctx.ctx.transport.write(str(e))

          if int(e) in range(200, 300):
            #return ...
            raise StopIteration(ctx.afterSender((yield ctx.ctx.command()), ctx.afterSender))

          #return ...
          raise StopIteration(state((yield ctx.ctx.command()), state))

      if 'RSET' == command.verb:
        ctx.ctx.transport.write(str(reply(250)))

        #return ...
        raise StopIteration(ctx.ctx.mail())

      #return ...
      raise StopIteration(ctx.ctx.start(command, state))

    def recipient(ctx, recipient):
      raise NotImplementedError

    @promise.continuate
    def afterSender(ctx, command, state):

      # Once started, a mail transaction consists of a transaction beginning
      # command, one or more RCPT commands, and a DATA command, in that order
      if 'RCPT' == command.verb:
        try:
          try:
            yield ctx.recipient(rfc5321.rcpt.match(str(command), 'mailbox ( localPart, domain, addressLiteral )'))

          # TODO Log
          except NotImplementedError:
            raise reply(502)

          except ValueError:
            raise reply(555)

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

    def content(ctx, content):
      raise NotImplementedError

    @promise.continuate
    def afterRecipient(ctx, command, state):
      if 'DATA' == command.verb:
        ctx.ctx.transport.write(str(reply(354)))

        while True:
          try:
            content, ctx.ctx.read = ctx.ctx.read.split('\r\n.\r\n', 1)

            break

          except ValueError:
            ctx.ctx.read += yield ctx.ctx.transport.protocol.dataReceived.shift()

        # When a line of mail text is received by the SMTP server, it checks
        # the line.  If the line is composed of a single period, it is treated
        # as the end of mail indicator.  If the first character is a period and
        # there are other characters on the line, the first character is
        # deleted

        # Lookbehind requires fixed width pattern
        content = re.sub('(^|\r\n)\.(?=.)', '\\1', content)

        try:
          try:
            yield ctx.content(content)

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
      raise StopIteration(ctx.afterSender(command, state))
