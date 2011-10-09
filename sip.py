import socket, untwisted
from qwer import *
from untwisted import dns, promise, rfc3261, udp

# Cache our domain
domain = socket.getfqdn()

class request:
  def __init__(ctx):
    ctx.header = untwisted.manyMap()

  __str__ = lambda ctx: ctx.method + ' ' + ctx.requestUri + ' ' + ctx.sipVersion + '\r\n' + '\r\n'.join('\r\n'.join(map((name + ': ').__add__, value)) for name, value in ctx.header) + '\r\n\r\n' + ctx.content

class response:
  def __init__(ctx):
    ctx.header = untwisted.manyMap()

  __int__ = lambda ctx: ctx.statusCode
  __str__ = lambda ctx: ctx.sipVersion + ' ' + str(ctx.statusCode) + ' ' + ctx.reasonPhrase + '\r\n' + '\r\n'.join('\r\n'.join(map((name + ': ').__add__, value)) for name, value in ctx.header) + '\r\n\r\n' + ctx.content

@promise.resume
def client(method, requestUri, initiator):
  match = qwer(rfc3261.requestUri, '$').match(requestUri, '( host, hostname, maddrParam, port )')

  # We define TARGET as the value of the maddr parameter of the URI, if
  # present, otherwise, the host value of the hostport component of the URI
  if match.maddrParam:
    target = match.maddrParam.host

  else:
    target = match.host

  if match.port:
    port = match.port

  elif target.hostname:
    try:
      result = yield dns.lookup('_sip._udp.' + str(target), dns.SRV)

    except dns.message as e:
      if dns.nameError != e.rcode:
        raise

      port = 'sip'

    else:
      target = result.answer.target
      port = result.answer.port

  else:
    port = 'sip'

  transport = yield udp.connect(str(target), port)()

  asdf = request()

  asdf.method = method
  asdf.requestUri = requestUri
  asdf.sipVersion = 'SIP/2.0'

  asdf.header.append('To', requestUri)
  asdf.header.append('From', initiator + ';tag=' + untwisted.randstr(6, '!%\'*+-.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_`abcdefghijklmnopqrstuvwxyz~'))
  asdf.header.append('Call-ID', untwisted.randstr(6, '!"%\'()*+-./0123456789:<>?ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]_`abcdefghijklmnopqrstuvwxyz{}~') + '@' + domain)
  asdf.header.append('CSeq', '0 ' + method)

  # A UAC MUST insert a Max-Forwards header field into each request it
  # originates with a value that SHOULD be 70
  asdf.header.append('Max-Forwards', '70')

  host, port = transport.socket.getsockname()
  sentBy = host + ':' + str(port)

  # The branch ID inserted by an element compliant with this specification MUST
  # always begin with the characters "z9hG4bK"
  #asdf.header.append('Via', 'SIP/2.0/UDP {};branch=z9hG4bK'.format(sentBy) + untwisted.randstr(6, '!%\'*+-.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_`abcdefghijklmnopqrstuvwxyz~'))
  asdf.header.append('Via', 'SIP/2.0/UDP {0};branch=z9hG4bK'.format(sentBy) + untwisted.randstr(6, '!%\'*+-.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_`abcdefghijklmnopqrstuvwxyz~'))

  asdf.content = ''

  transport.write(str(asdf))

  while True:
    recv = yield transport.recv()

    match = rfc3261.response.match(recv, '( sipVersion, statusCode, reasonPhrase, messageBody )')
    if int(match.statusCode) not in range(100, 200):
      result = response()

      result.sipVersion = str(match.sipVersion)
      result.statusCode = int(match.statusCode)
      result.reasonPhrase = str(match.reasonPhrase)

      result.content = str(match.messageBody)

      if int(result) not in range(200, 300):
        raise result

      #return ...
      raise StopIteration(result)
