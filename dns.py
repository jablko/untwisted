import re, untwisted
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

class header:
  __str__ = lambda ctx: chr(ctx.id >> 8) + chr(ctx.id & 0xff) + chr(ctx.qr << 7 | ctx.opcode << 3 | ctx.aa << 2 | ctx.tc << 1 | ctx.rd) + chr(ctx.ra << 7 | ctx.z << 4 | ctx.rcode) + chr(ctx.qdcount >> 8) + chr(ctx.qdcount & 0xff) + chr(ctx.ancount >> 8) + chr(ctx.ancount & 0xff) + chr(ctx.nscount >> 8) + chr(ctx.nscount & 0xff) + chr(ctx.arcount >> 8) + chr(ctx.arcount & 0xff)

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
  def __init__(ctx, qname, qtype, qclass):
    ctx.qname = qname
    ctx.qtype = qtype
    ctx.qclass = qclass

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
  pass

class oneMany:
  def __init__(ctx):
    ctx.asdf = []

    ctx.append = ctx.asdf.append
    ctx.__getitem__ = ctx.asdf.__getitem__
    ctx.__iter__ = ctx.asdf.__iter__
    ctx.__len__ = ctx.asdf.__len__

  def __getattr__(ctx, name):
    asdf, = ctx.asdf

    return getattr(asdf, name)

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
    ctx.header = header()
    ctx.question = oneMany()
    ctx.answer = oneMany()
    ctx.authority = oneMany()
    ctx.additional = oneMany()

  __str__ = lambda ctx: str(ctx.header) + ''.join(map(str, ctx.question)) + ''.join(map(str, ctx.answer)) + ''.join(map(str, ctx.authority)) + ''.join(map(str, ctx.additional))

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

      query.header.id = 0

      query.header.qr = 0
      query.header.opcode = 0
      query.header.aa = 0
      query.header.tc = 0
      query.header.rd = 1

      query.header.ra = 0
      query.header.z = 0
      query.header.rcode = 0

      query.header.qdcount = 1
      query.header.ancount = 0
      query.header.nscount = 0
      query.header.arcount = 0

      query.question.append(question(qname, qtype, qclass))

      transport.write(str(query))

      ctx.recv = yield transport.recv()

      response = message()

      response.header.id = ord(ctx.recv[0]) << 8 | ord(ctx.recv[1])

      response.header.qr = ord(ctx.recv[2]) >> 7
      response.header.opcode = ord(ctx.recv[2]) >> 3 & 0xf
      response.header.aa = ord(ctx.recv[2]) >> 2 & 1
      response.header.tc = ord(ctx.recv[2]) >> 1 & 1
      response.header.rd = ord(ctx.recv[2]) & 1

      response.header.ra = ord(ctx.recv[3]) >> 7
      response.header.z = ord(ctx.recv[3]) >> 4 & 7
      response.header.rcode = ord(ctx.recv[3]) & 0xf

      response.header.qdcount = ord(ctx.recv[4]) << 8 | ord(ctx.recv[5])
      response.header.ancount = ord(ctx.recv[6]) << 8 | ord(ctx.recv[7])
      response.header.nscount = ord(ctx.recv[8]) << 8 | ord(ctx.recv[9])
      response.header.arcount = ord(ctx.recv[10]) << 8 | ord(ctx.recv[11])

      ctx.offset = 12

      for _ in range(response.header.qdcount):
        ctx.domainName(ctx.offset)

        ctx.offset += 4

      for _ in range(response.header.ancount):
        itm = rr()

        ctx.domainName(ctx.offset)

        itm.type = ord(ctx.recv[ctx.offset]) << 8 | ord(ctx.recv[ctx.offset + 1])
        itm.rdlength = ord(ctx.recv[ctx.offset + 8]) << 8 | ord(ctx.recv[ctx.offset + 9])

        ctx.offset += 10

        if A == itm.type:

          #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
          # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
          # |                    ADDRESS                    |
          # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

          itm.address = '.'.join(map(untwisted.compose(str, ord), ctx.recv[ctx.offset:ctx.offset + 4]))

          ctx.offset += 4

        elif NS == itm.type:

          #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
          # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
          # /                                               /
          # /                    NSDNAME                    /
          # /                                               /
          # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

          itm.nsdname = ctx.domainName(ctx.offset)

        elif PTR == itm.type:

          #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
          # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
          # /                                               /
          # /                   PTRDNAME                    /
          # /                                               /
          # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

          itm.ptrdname = ctx.domainName(ctx.offset)

        elif MX == itm.type:

          #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
          # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
          # |                  PREFERENCE                   |
          # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
          # /                                               /
          # /                   EXCHANGE                    /
          # /                                               /
          # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

          itm.preference = ord(ctx.recv[ctx.offset]) << 8 | ord(ctx.recv[ctx.offset + 1])

          ctx.offset += 2

          itm.exchange = ctx.domainName(ctx.offset)

        elif SRV == itm.type:
          itm.priority = ord(ctx.recv[ctx.offset]) << 8 | ord(ctx.recv[ctx.offset + 1])
          itm.weight = ord(ctx.recv[ctx.offset + 2]) << 8 | ord(ctx.recv[ctx.offset + 3])
          itm.port = ord(ctx.recv[ctx.offset + 4]) << 8 | ord(ctx.recv[ctx.offset + 5])

          ctx.offset += 6

          itm.target = ctx.domainName(ctx.offset)

        response.answer.append(itm)

      if response.header.rcode:
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
