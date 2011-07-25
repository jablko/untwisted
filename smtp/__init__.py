import re, socket, untwisted
from untwisted import promise, rfc5321

# Cache our domain
domain = socket.getfqdn()

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
        yield ctx.ehloCmd()

      except reply as e:
        if int(e) not in (500, 502):
          raise

        yield ctx.heloCmd()

      while True:
        try:
          yield ctx.mail()

        except StopIteration:
          break

      #return ...
      raise StopIteration(ctx.quitCmd())

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
    prev.then(ctx.head)

    clone = promise.promise()
    ctx.head.then(clone)

    @ctx.head.then
    def _(_):
      try:
        prev.traceback = clone.traceback

      except AttributeError:
        pass

      prev.args = clone.args
      prev.kwds = clone.kwds

    @ctx.head.then
    @promise.continuate
    def _(_):
      while True:
        try:
          replyLine = rfc5321.replyLine.match(ctx.read, '( replyCode, textstring )')

          break

        except ValueError:
          ctx.read += yield ctx.transport.protocol.dataReceived.shift()

      ctx.read = ctx.read[len(replyLine):]

      @clone.then
      def _(_):
        result = reply(int(replyLine.replyCode), *map(str, replyLine.textstring))
        if int(result) not in expect:
          raise result

        return result

      #return ...
      raise StopIteration(clone)

    return ctx.head

  def ehloCmd(ctx):
    ctx.transport.write(str(command('EHLO', domain)))

    return ctx.reply()

  def heloCmd(ctx):
    ctx.transport.write(str(command('HELO', domain)))

    return ctx.reply()

  class mail:
    class __metaclass__(type):
      __get__ = untwisted.ctxual

      @promise.continuate
      def __call__(ctx):
        ctx = type.__call__(ctx)

        result = yield ctx.mail()
        if not isinstance(result, reply):
          yield ctx.mailCmd(result)

        result = yield ctx.recipient()
        if not isinstance(result, reply):
          yield ctx.rcptCmd(result)

        while True:
          try:
            result = yield ctx.recipient()

          except StopIteration:
            break

          if not isinstance(result, reply):
            yield ctx.rcptCmd(result)

        result = yield ctx.data()
        if not isinstance(result, reply):
          #return ...
          raise StopIteration(ctx.dataCmd(result))

        #return ...
        raise StopIteration(result)

    def mailCmd(ctx, mailbox):
      #ctx.ctx.transport.write(str(command('MAIL FROM:<{}>'.format(mailbox))))
      ctx.ctx.transport.write(str(command('MAIL FROM:<{0}>'.format(mailbox))))

      return ctx.ctx.reply()

    def mail(ctx):
      raise NotImplementedError

    def rcptCmd(ctx, mailbox):
      #ctx.ctx.transport.write(str(command('RCPT TO:<{}>'.format(mailbox))))
      ctx.ctx.transport.write(str(command('RCPT TO:<{0}>'.format(mailbox))))

      return ctx.ctx.reply()

    def recipient(ctx):
      raise NotImplementedError

    @promise.continuate
    def dataCmd(ctx, data):
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
      data = re.sub('(^|\r\n)\.', '\\1..', data)

      # An extra <CRLF> MUST NOT be added, as that would cause an empty line to
      # be added to the message.  The only exception to this rule would arise
      # if the message body were passed to the originating SMTP-sender with a
      # final "line" that did not end in <CRLF>; in that case, the originating
      # SMTP system MUST either reject the message as invalid or add <CRLF> in
      # order to have the receiving SMTP server recognize the "end of data"
      # condition
      if '\r\n' != data[-2:]:
        data += '\r\n'

      data += '.\r\n'

      ctx.ctx.transport.write(data)

      #return ...
      raise StopIteration(ctx.ctx.reply())

    def data(ctx):
      raise NotImplementedError

  def rsetCmd(ctx):
    ctx.transport.write(str(command('RSET')))

    return ctx.reply()

  def quitCmd(ctx):
    ctx.transport.write(str(command('QUIT')))

    return ctx.reply()

class pipeline(client):
  pipeline = False

  @promise.continuate
  def ehloCmd(ctx):
    result = yield client.ehloCmd(ctx)

    ctx.pipeline = 'PIPELINING' in result.text[1:]

    #return ...
    raise StopIteration(result)

  class mail(client.mail):
    def mailCmd(ctx, mailbox):
      result = client.mail.mailCmd(ctx, mailbox)
      if ctx.ctx.pipeline:
        result = promise.promise()(result)

      return result

    def rcptCmd(ctx, mailbox):
      result = client.mail.rcptCmd(ctx, mailbox)
      if ctx.ctx.pipeline:
        result = promise.promise()(result)

      return result

    @promise.continuate
    def dataCmd(ctx, data):
      ctx.ctx.transport.write(str(command('DATA')))

      yield ctx.ctx.reply(range(300, 400))

      data = re.sub('(^|\r\n)\.', '\\1..', data)

      if '\r\n' != data[-2:]:
        data += '\r\n'

      data += '.\r\n'

      ctx.ctx.transport.write(data)

      result = ctx.ctx.reply()
      if ctx.ctx.pipeline:
        result = promise.promise()(result)

      #return ...
      raise StopIteration(result)

  def rsetCmd(ctx):
    result = client.rsetCmd(ctx)
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

    def mail(ctx, mailbox):
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
            yield ctx.mail(rfc5321.mail.match(str(command), 'mailbox ( localPart, domain, addressLiteral )'))

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

    @promise.continuate
    def afterMail(ctx, command, state):

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

    def data(ctx, data):
      raise NotImplementedError

    @promise.continuate
    def afterRecipient(ctx, command, state):
      if 'DATA' == command.verb:
        ctx.ctx.transport.write(str(reply(354)))

        while True:
          try:
            data, ctx.ctx.read = ctx.ctx.read.split('\r\n.\r\n', 1)

            break

          except ValueError:
            ctx.ctx.read += yield ctx.ctx.transport.protocol.dataReceived.shift()

        # When a line of mail text is received by the SMTP server, it checks
        # the line.  If the line is composed of a single period, it is treated
        # as the end of mail indicator.  If the first character is a period and
        # there are other characters on the line, the first character is
        # deleted

        # Lookbehind requires fixed width pattern
        data = re.sub('(^|\r\n)\.(?=.)', '\\1', data)

        try:
          try:
            yield ctx.data(data)

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
