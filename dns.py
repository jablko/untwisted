import re, socket, untwisted
from untwisted import promise, udp

# TYPE fields are used in resource records.  Note that these types are a subset
# of QTYPEs
A = 1
NS = 2
MD = 3
MF = 4
CNAME = 5
SOA = 6
MB = 7
MG = 8
MR = 9
NULL = 10
WKS = 11
PTR = 12
HINFO = 13
MINFO = 14
MX = 15
TXT = 16

# Here is the format of the SRV RR, whose DNS type code is 33
SRV = 33

# CLASS fields appear in resource records.  The following CLASS mnemonics and
# values are defined
IN = 1
CS = 2
CH = 3
HS = 4

#   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
# +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
# /                                               /
# /                     QNAME                     /
# /                                               /
# +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
# |                     QTYPE                     |
# +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
# |                     QCLASS                    |
# +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

class question:
  __metaclass__ = type

  def __init__(ctx, *args):
    if args:
      try:
        ctx.qname, ctx.qtype, ctx.qclass = args

      except ValueError:
        try:
          ctx.qname, ctx.qtype = args

        except ValueError:
          ctx.qname, = args

  __delitem__ = object.__delattr__
  __getitem__ = object.__getattribute__
  __setitem__ = object.__setattr__

  def __str__(ctx):
    result = ''.join(chr(len(label)) + label for label in ctx.qname.split('.'))
    if not ctx.qname.endswith('.'):
      result += '\0'

    return result + chr(ctx.qtype >> 8) + chr(ctx.qtype & 0xff) + chr(ctx.qclass >> 8) + chr(ctx.qclass & 0xff)

#   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
# +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
# /                                               /
# /                     NAME                      /
# /                                               /
# +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
# |                     TYPE                      |
# +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
# |                     CLASS                     |
# +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
# |                      TTL                      |
# |                                               |
# +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
# |                   RDLENGTH                    |
# +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
# /                                               /
# /                     RDATA                     /
# /                                               /
# +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

class rr:
  __metaclass__ = type

  __delitem__ = object.__delattr__
  __getitem__ = object.__getattribute__
  __setitem__ = object.__setattr__

# +---------------------+
# |       Header        |
# +---------------------+
# |      Question       | Question for the name server
# +---------------------+
# |       Answer        | RRs answering question
# +---------------------+
# |      Authority      | RRs pointing toward an authority
# +---------------------+
# |     Additional      | RRs holding additional information
# +---------------------+

class message:
  def __init__(ctx):
    ctx.question = untwisted.oneMany()
    ctx.answer = untwisted.oneMany()
    ctx.authority = untwisted.oneMany()
    ctx.additional = untwisted.oneMany()

  #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
  # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
  # |                      ID                       |
  # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
  # |QR|   Opcode  |AA|TC|RD|RA|   Z    |   RCODE   |
  # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
  # |                    QDCOUNT                    |
  # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
  # |                    ANCOUNT                    |
  # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
  # |                    NSCOUNT                    |
  # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
  # |                    ARCOUNT                    |
  # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

  def __str__(ctx):
    qdcount = len(ctx.question)
    ancount = len(ctx.answer)
    nscount = len(ctx.authority)
    arcount = len(ctx.additional)

    return ctx.id + chr(ctx.qr << 7 | ctx.opcode << 3 | ctx.aa << 2 | ctx.tc << 1 | ctx.rd) + chr(ctx.ra << 7 | ctx.z << 4 | ctx.rcode) + chr(qdcount >> 8) + chr(qdcount & 0xff) + chr(ancount >> 8) + chr(ancount & 0xff) + chr(nscount >> 8) + chr(nscount & 0xff) + chr(arcount >> 8) + chr(arcount & 0xff) + ''.join(map(str, ctx.question)) + ''.join(map(str, ctx.answer)) + ''.join(map(str, ctx.authority)) + ''.join(map(str, ctx.additional))

server = []

resolvConf = open('/etc/resolv.conf').read()

pos = 0
while pos < len(resolvConf):
  match = re.compile('^nameserver\s+([^\s#]+)', re.M).search(resolvConf, pos)
  if not match:
    break

  server.append(match.group(1))

  pos = match.end()

# Workaround PEP 3104 with class
class lookup:
  class __metaclass__(type):

    @promise.resume
    def __call__(ctx, qname, qtype=A, qclass=IN, server=server[0]):
      ctx = type.__call__(ctx)

      transport = yield udp.connect(server, 'domain')()

      query = message()

      query.id = '\0\0'

      query.qr = 0
      query.opcode = 0
      query.aa = 0
      query.tc = 0
      query.rd = 1

      query.ra = 0
      query.z = 0
      query.rcode = 0

      query.question.append(question(qname, qtype, qclass))

      transport.write(str(query))

      ctx.recv = yield transport.recv()

      response = message()

      response.id = ctx.recv[:2]

      response.qr = ord(ctx.recv[2]) >> 7
      response.opcode = ord(ctx.recv[2]) >> 3 & 0xf
      response.aa = ord(ctx.recv[2]) >> 2 & 1
      response.tc = ord(ctx.recv[2]) >> 1 & 1
      response.rd = ord(ctx.recv[2]) & 1

      response.ra = ord(ctx.recv[3]) >> 7
      response.z = ord(ctx.recv[3]) >> 4 & 7
      response.rcode = ord(ctx.recv[3]) & 0xf

      qdcount = ord(ctx.recv[4]) << 8 | ord(ctx.recv[5])
      ancount = ord(ctx.recv[6]) << 8 | ord(ctx.recv[7])
      nscount = ord(ctx.recv[8]) << 8 | ord(ctx.recv[9])
      arcount = ord(ctx.recv[10]) << 8 | ord(ctx.recv[11])

      ctx.offset = 12

      for _ in range(qdcount):
        response.question.append(ctx.question(ctx.offset))

      for _ in range(ancount):
        response.answer.append(ctx.rr(ctx.offset))

      for _ in range(nscount):
        response.authority.append(ctx.rr(ctx.offset))

      for _ in range(arcount):
        response.additional.append(ctx.rr(ctx.offset))

      if response.rcode:
        raise response

      #return ...
      raise StopIteration(response)

  def domainName(ctx, offset):
    result = ''
    while True:
      length = ord(ctx.recv[offset])

      # An entire domain name or a list of labels at the end of a domain name
      # is replaced with a pointer to a prior occurance of the same name
      if 0xbf < length:
        try:
          return result + ctx.domainName((length & 0x3f) << 8 | ord(ctx.recv[offset + 1]))

        finally:
          ctx.offset = offset + 2

      offset += 1

      if not length:
        ctx.offset = offset

        return result

      result += ctx.recv[offset:offset + length] + '.'

      offset += length

  def question(ctx, offset):
    result = question()

    result.qname = ctx.domainName(offset)
    result.qtype = ord(ctx.recv[ctx.offset]) << 8 | ord(ctx.recv[ctx.offset + 1])
    result.qclass = ord(ctx.recv[ctx.offset + 2]) << 8 | ord(ctx.recv[ctx.offset + 3])

    ctx.offset += 4

    return result

  def rr(ctx, offset):
    result = rr()

    result.name = ctx.domainName(offset)
    result.type = ord(ctx.recv[ctx.offset]) << 8 | ord(ctx.recv[ctx.offset + 1])
    result['class'] = ord(ctx.recv[ctx.offset + 2]) << 8 | ord(ctx.recv[ctx.offset + 3])
    result.ttl = reduce(lambda result, itm: result << 8 | itm, map(ord, ctx.recv[ctx.offset + 4:ctx.offset + 8]))
    result.rdlength = ord(ctx.recv[ctx.offset + 8]) << 8 | ord(ctx.recv[ctx.offset + 9])

    ctx.offset += 10

    if A == result.type:

      #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # |                    ADDRESS                    |
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

      result.address = socket.inet_ntop(socket.AF_INET, ctx.recv[ctx.offset:ctx.offset + 4])

      ctx.offset += 4

      return result

    if NS == result.type:

      #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # /                                               /
      # /                    NSDNAME                    /
      # /                                               /
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

      result.nsdname = ctx.domainName(ctx.offset)

      return result

    if result.type in (MD, MF, MB):

      #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # /                                               /
      # /                    MADNAME                    /
      # /                                               /
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

      result.madname = ctx.domainName(ctx.offset)

      return result

    if CNAME == result.type:

      #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # /                                               /
      # /                     CNAME                     /
      # /                                               /
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

      result.cname = ctx.domainName(ctx.offset)

      return result

    if SOA == result.type:

      #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # /                                               /
      # /                     MNAME                     /
      # /                                               /
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # /                                               /
      # /                     RNAME                     /
      # /                                               /
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # |                    SERIAL                     |
      # |                                               |
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # |                    REFRESH                    |
      # |                                               |
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # |                     RETRY                     |
      # |                                               |
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # |                    EXPIRE                     |
      # |                                               |
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # |                    MINIMUM                    |
      # |                                               |
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

      result.mname = ctx.domainName(ctx.offset)
      result.rname = ctx.domainName(ctx.offset)
      result.serial = reduce(lambda result, itm: result << 8 | itm, map(ord, ctx.recv[ctx.offset:ctx.offset + 4]))
      result.refresh = reduce(lambda result, itm: result << 8 | itm, map(ord, ctx.recv[ctx.offset + 4:ctx.offset + 8]))
      result.retry = reduce(lambda result, itm: result << 8 | itm, map(ord, ctx.recv[ctx.offset + 8:ctx.offset + 12]))
      result.expire = reduce(lambda result, itm: result << 8 | itm, map(ord, ctx.recv[ctx.offset + 12:ctx.offset + 16]))
      result.minimum = reduce(lambda result, itm: result << 8 | itm, map(ord, ctx.recv[ctx.offset + 16:ctx.offset + 20]))

      ctx.offset += 20

      return result

    if MG == result.type:

      #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # /                                               /
      # /                    MGMNAME                    /
      # /                                               /
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

      result.mgmname = ctx.domainName(ctx.offset)

      return result

    if MR == result.type:

      #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # /                                               /
      # /                    NEWNAME                    /
      # /                                               /
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

      result.newname = ctx.domainName(ctx.offset)

      return result

    if PTR == result.type:

      #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # /                                               /
      # /                   PTRDNAME                    /
      # /                                               /
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

      result.ptrdname = ctx.domainName(ctx.offset)

      return result

    if HINFO == result.type:

      #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # /                      CPU                      /
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # /                      OS                       /
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

      length = ord(ctx.recv[ctx.offset])

      ctx.offset += 1

      result.cpu = ctx.recv[ctx.offset:ctx.offset + length]

      ctx.offset += length

      length = ord(ctx.recv[ctx.offset])

      ctx.offset += 1

      result.os = ctx.recv[ctx.offset:ctx.offset + length]

      ctx.offset += length

      return result

    if MINFO == result.type:

      #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # /                                               /
      # /                    RMAILBX                    /
      # /                                               /
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # /                                               /
      # /                    EMAILBX                    /
      # /                                               /
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

      result.rmailbx = ctx.domainName(ctx.offset)
      result.emailbx = ctx.domainName(ctx.offset)

      return result

    if MX == result.type:

      #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # |                  PREFERENCE                   |
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # /                                               /
      # /                   EXCHANGE                    /
      # /                                               /
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

      result.preference = ord(ctx.recv[ctx.offset]) << 8 | ord(ctx.recv[ctx.offset + 1])

      ctx.offset += 2

      result.exchange = ctx.domainName(ctx.offset)

      return result

    if TXT == result.type:

      #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # /                   TXT-DATA                    /
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

      length = ord(ctx.recv[ctx.offset])

      ctx.offset += 1

      result.txtData = ctx.recv[ctx.offset:ctx.offset + length]

      ctx.offset += length

      return result

    if SRV == result.type:
      result.priority = ord(ctx.recv[ctx.offset]) << 8 | ord(ctx.recv[ctx.offset + 1])
      result.weight = ord(ctx.recv[ctx.offset + 2]) << 8 | ord(ctx.recv[ctx.offset + 3])
      result.port = ord(ctx.recv[ctx.offset + 4]) << 8 | ord(ctx.recv[ctx.offset + 5])

      ctx.offset += 6

      result.target = ctx.domainName(ctx.offset)

      return result

    ctx.offset += result.rdlength

    return result
