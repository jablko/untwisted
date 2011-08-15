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
      ctx.text = args or { 354: ('Start mail input; end with <CRLF>.<CRLF>',) }[code]

    except KeyError:
      ctx.text = ()

  __int__ = lambda ctx: ctx.code

  def __str__(ctx):
    result = str(ctx.code)

    try:
      result += ' ' + ctx.text[-1]

    except IndexError:
      pass

    else:
      result = ''.join(str(ctx.code) + '-' + text + '\r\n' for text in ctx.text[:-1]) + result

    return result + '\r\n'

class enhance(reply):
  def __init__(ctx, basic, enhance, *args):
    try:
      text = args or {
        (221, '2.5.0'): ('Service closing transmission channel',),
        (502, '5.5.1'): ('Command not implemented',),
        (503, '5.5.1'): ('Bad sequence of commands',),
        (500, '5.5.2'): ('Syntax error, command unrecognized',),
        (555, '5.5.4'): ('MAIL FROM/RCPT TO parameters not recognized or not implemented',) }[basic, enhance]

    except KeyError:
      try:
        text = {
          '2.1.0': ('Success',),
          '2.1.5': ('Destination address valid',),
          '2.5.0': ('Success',),
          '2.6.0': ('Success',) }[enhance]

      except KeyError:
        return reply.__init__(ctx, basic, enhance)

    reply.__init__(ctx, basic, *map((enhance + ' ').__add__, text))

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
    ctx.head = result = promise.promise()

    prev.then(result.then(promise.promise()))

    @result.then
    def _(clone):
      try:
        prev.traceback = clone.traceback

      except AttributeError:
        pass

      prev.args = clone.args
      prev.kwds = clone.kwds

      def callback(read):
        try:
          replyLine = rfc5321.replyLine.match(read, '( replyCode, textstring )')

        except ValueError:
          asdf.callback.insert(0, callback)

          return ctx.transport.protocol.dataReceived.shift().then(read.__add__)

        ctx.read = read[len(replyLine):]

        @clone.then
        def _(_):
          result = reply(int(replyLine.replyCode), *map(str, replyLine.textstring))
          if int(result) not in expect:
            raise result

          return result

        return clone

      asdf = promise.promise().then(callback)

      return asdf(ctx.read)

    return result

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
          raise StopIteration((yield ctx.data(result)))

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

    # Aesthetics : ( DATA involves two replies, and we may need to distinguish
    # because only if the second reply is an error is the transaction complete.
    # Also the first reply must be received before more commands can be issued,
    # but the second reply can start a pipeline command group.  Don't want to
    # split .data() into two methods because they're *always* called together.
    # So far no need for first reply value (it should always be 354 unless it's
    # an error) - just whether it's an error, and when it's received.  So
    # .data() returns a promise that's fulfilled when the first reply is
    # received.  If the first reply isn't an error, then it's fulfilled with
    # another promise, which is fulfilled when the second reply is received
    def data(ctx, content):
      ctx.ctx.transport.write(str(command('DATA')))

      # Since some servers may generate other replies under special
      # circumstances, and to allow for future extension, SMTP clients SHOULD,
      # when possible, interpret only the first digit of the reply and MUST be
      # prepared to deal with unrecognized reply codes by interpreting the
      # first digit only
      result = ctx.ctx.reply(range(300, 400))

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

      @result.then
      def _(_):
        ctx.ctx.transport.write(content)

        return promise.promise()(ctx.ctx.reply())

      return result

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

  def ehlo(ctx):
    if not ctx.pipeline:
      prev = ctx.head
      ctx.head = result = promise.promise()

      prev.then(result.then(promise.promise()))

      @result.then
      def _(clone):
        try:
          prev.traceback = clone.traceback

        except AttributeError:
          pass

        prev.args = clone.args
        prev.kwds = clone.kwds

        @clone.then
        def _(_):
          ctx.transport.write(str(command('EHLO', domain)))

          expect = range(200, 300)

          def callback(read):
            try:
              replyLine = rfc5321.replyLine.match(read, '( replyCode, textstring )')

            except ValueError:
              asdf.callback.insert(0, callback)

              return ctx.transport.protocol.dataReceived.shift().then(read.__add__)

            ctx.read = read[len(replyLine):]

            result = reply(int(replyLine.replyCode), *map(str, replyLine.textstring))
            if int(result) not in expect:
              raise result

            ctx.pipeline = 'PIPELINING' in result.text[1:]

            return result

          asdf = promise.promise().then(callback)

          return asdf(ctx.read)

        return clone

      return result

    result = client.ehlo(ctx)

    @result.then
    def _(result):
      ctx.pipeline = 'PIPELINING' in result.text[1:]

      return result

    return result

  class mail(client.mail):
    class __metaclass__(client.mail.__metaclass__):

      @promise.continuate
      def __call__(ctx):
        ctx = type.__call__(ctx)

        result = yield ctx.sender()
        if not isinstance(result, reply):
          ctx.mail(result)

        result = yield ctx.recipient()
        if not isinstance(result, reply):
          ctx.rcpt(result)

        while True:
          try:
            result = yield ctx.recipient()

          except StopIteration:
            break

          if not isinstance(result, reply):
            ctx.rcpt(result)

        result = yield ctx.content()
        if not isinstance(result, reply):
          #return ...
          raise StopIteration(ctx.data(result))

        #return ...
        raise StopIteration(result)

    def mail(ctx, sender):
      if not ctx.ctx.pipeline:
        prev = ctx.ctx.head
        ctx.ctx.head = result = promise.promise()

        prev.then(result.then(promise.promise()))

        @result.then
        def _(clone):
          try:
            prev.traceback = clone.traceback

          except AttributeError:
            pass

          prev.args = clone.args
          prev.kwds = clone.kwds

          @clone.then
          def _(_):
            #ctx.ctx.transport.write(str(command('MAIL FROM:<{}>'.format(sender))))
            ctx.ctx.transport.write(str(command('MAIL FROM:<{0}>'.format(sender))))

            expect = range(200, 300)

            def callback(read):
              try:
                replyLine = rfc5321.replyLine.match(read, '( replyCode, textstring )')

              except ValueError:
                asdf.callback.insert(0, callback)

                return ctx.ctx.transport.protocol.dataReceived.shift().then(read.__add__)

              ctx.ctx.read = read[len(replyLine):]

              result = reply(int(replyLine.replyCode), *map(str, replyLine.textstring))
              if int(result) not in expect:
                raise result

              return result

            asdf = promise.promise().then(callback)

            return asdf(ctx.ctx.read)

          return clone

        return result

      return client.mail.mail(ctx, sender)

    def rcpt(ctx, recipient):
      if not ctx.ctx.pipeline:
        prev = ctx.ctx.head
        ctx.ctx.head = result = promise.promise()

        prev.then(result.then(promise.promise()))

        @result.then
        def _(clone):
          try:
            prev.traceback = clone.traceback

          except AttributeError:
            pass

          prev.args = clone.args
          prev.kwds = clone.kwds

          @clone.then
          def _(_):
            #ctx.ctx.transport.write(str(command('RCPT TO:<{}>'.format(recipient))))
            ctx.ctx.transport.write(str(command('RCPT TO:<{0}>'.format(recipient))))

            expect = range(200, 300)

            def callback(read):
              try:
                replyLine = rfc5321.replyLine.match(read, '( replyCode, textstring )')

              except ValueError:
                asdf.callback.insert(0, callback)

                return ctx.ctx.transport.protocol.dataReceived.shift().then(read.__add__)

              ctx.ctx.read = read[len(replyLine):]

              result = reply(int(replyLine.replyCode), *map(str, replyLine.textstring))
              if int(result) not in expect:
                raise result

              return result

            asdf = promise.promise().then(callback)

            return asdf(ctx.ctx.read)

          return clone

        return result

      return client.mail.rcpt(ctx, recipient)

    def data(ctx, content):
      if not ctx.ctx.pipeline:
        content = re.sub('(^|\r\n)\.', '\\1..', content)

        if '\r\n' != content[-2:]:
          content += '\r\n'

        content += '.\r\n'

        prev = ctx.ctx.head
        ctx.ctx.head = result = promise.promise()

        prev.then(result.then(promise.promise()))

        @result.then
        def _(clone):
          try:
            prev.traceback = clone.traceback

          except AttributeError:
            pass

          prev.args = clone.args
          prev.kwds = clone.kwds

          @clone.then
          def _(_):
            ctx.ctx.transport.write(str(command('DATA')))

            expect = range(300, 400)

            def callback(read):
              try:
                replyLine = rfc5321.replyLine.match(read, '( replyCode, textstring )')

              except ValueError:
                asdf.callback.insert(0, callback)

                return ctx.ctx.transport.protocol.dataReceived.shift().then(read.__add__)

              ctx.ctx.read = read[len(replyLine):]

              result = reply(int(replyLine.replyCode), *map(str, replyLine.textstring))
              if int(result) not in expect:
                raise result

              ctx.ctx.transport.write(content)

              return promise.promise()(ctx.ctx.reply())

            asdf = promise.promise().then(callback)

            return asdf(ctx.ctx.read)

          return clone

        return result

      return client.mail.data(ctx, content)

  def rset(ctx):
    if not ctx.pipeline:
      prev = ctx.head
      ctx.head = result = promise.promise()

      prev.then(result.then(promise.promise()))

      @result.then
      def _(clone):
        try:
          prev.traceback = clone.traceback

        except AttributeError:
          pass

        prev.args = clone.args
        prev.kwds = clone.kwds

        @clone.then
        def _(_):
          ctx.transport.write(str(command('RSET')))

          expect = range(200, 300)

          def callback(read):
            try:
              replyLine = rfc5321.replyLine.match(read, '( replyCode, textstring )')

            except ValueError:
              asdf.callback.insert(0, callback)

              return ctx.transport.protocol.dataReceived.shift().then(read.__add__)

            ctx.read = read[len(replyLine):]

            result = reply(int(replyLine.replyCode), *map(str, replyLine.textstring))
            if int(result) not in expect:
              raise result

            return result

          asdf = promise.promise().then(callback)

          return asdf(ctx.read)

        return clone

      return result

    return client.rset(ctx)

  def quit(ctx):
    if not ctx.pipeline:
      prev = ctx.head
      ctx.head = result = promise.promise()

      prev.then(result.then(promise.promise()))

      @result.then
      def _(clone):
        try:
          prev.traceback = clone.traceback

        except AttributeError:
          pass

        prev.args = clone.args
        prev.kwds = clone.kwds

        @clone.then
        def _(_):
          ctx.transport.write(str(command('QUIT')))

          expect = range(200, 300)

          def callback(read):
            try:
              replyLine = rfc5321.replyLine.match(read, '( replyCode, textstring )')

            except ValueError:
              asdf.callback.insert(0, callback)

              return ctx.transport.protocol.dataReceived.shift().then(read.__add__)

            ctx.read = read[len(replyLine):]

            result = reply(int(replyLine.replyCode), *map(str, replyLine.textstring))
            if int(result) not in expect:
              raise result

            return result

          asdf = promise.promise().then(callback)

          return asdf(ctx.read)

        return clone

      return result

    return client.quit(ctx)

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

  def command(ctx):
    def callback(read):
      try:
        result, ctx.read = read.split('\r\n', 1)

      except ValueError:
        asdf.callback.insert(0, callback)

        return ctx.transport.protocol.dataReceived.shift().then(read.__add__)

      result = command(result)

      return result

    asdf = promise.promise().then(callback)

    return asdf(ctx.read)

  @promise.continuate
  def start(ctx, command, state):
    if 'EHLO' == command.verb:
      #ctx.transport.write(str(reply(250, '{} Success'.format(domain), 'ENHANCEDSTATUSCODES', 'PIPELINING')))
      ctx.transport.write(str(reply(250, '{0} Success'.format(domain), 'ENHANCEDSTATUSCODES', 'PIPELINING')))

      #return ...
      raise StopIteration(ctx.mail())

    if 'HELO' == command.verb:

      # Servers MUST NOT return the extended EHLO-style response to a HELO
      # command
      #ctx.transport.write(str(reply(250, '{} Success'.format(domain))))
      ctx.transport.write(str(reply(250, '{0} Success'.format(domain))))

      #return ...
      raise StopIteration(ctx.mail())

    if command.verb in ('MAIL', 'RCPT', 'DATA'):
      ctx.transport.write(str(enhance(503, '5.5.1')))

      #return ...
      raise StopIteration(state((yield ctx.command()), state))

    if command.verb in ('RSET', 'NOOP'):
      ctx.transport.write(str(enhance(250, '2.5.0')))

      #return ...
      raise StopIteration(state((yield ctx.command()), state))

    if command.verb in ('VRFY', 'EXPN', 'HELP'):
      ctx.transport.write(str(enhance(502, '5.5.1')))

      #return ...
      raise StopIteration(state((yield ctx.command()), state))

    if 'QUIT' == command.verb:
      ctx.transport.write(str(enhance(221, '2.5.0')))

      #return ...
      raise StopIteration(ctx.transport.loseConnection())

    # TODO Log?
    ctx.transport.write(str(enhance(500, '5.5.2')))

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
            raise enhance(502, '5.5.1')

          except ValueError:
            raise enhance(555, '5.5.4')

          raise enhance(250, '2.1.0')

        except reply as e:
          ctx.ctx.transport.write(str(e))

          if int(e) in range(200, 300):
            #return ...
            raise StopIteration(ctx.afterSender((yield ctx.ctx.command()), ctx.afterSender))

          #return ...
          raise StopIteration(state((yield ctx.ctx.command()), state))

      if 'RSET' == command.verb:
        ctx.ctx.transport.write(str(enhance(250, '2.5.0')))

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
            raise enhance(502, '5.5.1')

          except ValueError:
            raise enhance(555, '5.5.4')

          raise enhance(250, '2.1.5')

        except reply as e:
          ctx.ctx.transport.write(str(e))

          if int(e) in range(200, 300):
            #return ...
            raise StopIteration(ctx.afterRecipient((yield ctx.ctx.command()), ctx.afterRecipient))

          #return ...
          raise StopIteration(state((yield ctx.ctx.command()), state))

      if 'RSET' == command.verb:
        ctx.ctx.transport.write(str(enhance(250, '2.5.0')))

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
            raise enhance(502, '5.5.1')

          raise enhance(250, '2.6.0')

        except reply as e:
          ctx.ctx.transport.write(str(e))

          # Receipt of the end of mail data indication requires the server to
          # process the stored mail transaction information.  This processing
          # consumes the information in the reverse-path buffer, the
          # forward-path buffer, and the mail data buffer, and on the
          # completion of this command these buffers are cleared

          #return ...
          raise StopIteration(ctx.ctx.mail())

      #return ...
      raise StopIteration(ctx.afterSender(command, state))
