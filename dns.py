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
  pass

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
  pass

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
    ctx.__iter__ = ctx.asdf.__iter__

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

server = []

resolvConf = open('/etc/resolv.conf').read()

pos = 0
while pos < len(resolvConf):
  match = re.compile('^nameserver\s+([^\s#]+)', re.M).search(resolvConf, pos)
  if not match:
    break

  server.append(match.group(1))

  pos = match.end()

@promise.resume
def lookup(qname, qtype=A, qclass=IN, server=server[0]):
  transport = yield udp.connect(server, 'domain')()

  # QR: 0, Opcode: 0, AA: 0, TC: 0, RD: 1, RA: 0, Z: 0, RCODE: 0
  header = '\0\0\1\0\0\1\0\0\0\0\0\0'

  question = ''.join((
    ''.join(chr(len(label)) + label for label in qname.split('.')), '\0',
    chr(qtype >> 8), chr(qtype & 0xff),
    chr(qclass >> 8), chr(qclass & 0xff)))

  transport.write(header + question)

  recv = yield transport.recv()

  response = message()

  response.header.qdcount = (ord(recv[4]) << 8) + ord(recv[5])
  response.header.ancount = (ord(recv[6]) << 8) + ord(recv[7])
  response.header.nscount = (ord(recv[8]) << 8) + ord(recv[9])
  response.header.arcount = (ord(recv[10]) << 8) + ord(recv[11])

  recv = recv[12:]

  for _ in range(response.header.qdcount):
    while True:
      length = ord(recv[0])

      # An entire domain name or a list of labels at the end of a domain name
      # is replaced with a pointer to a prior occurance of the same name
      if 0xbf < length:
        recv = recv[2:]

        break

      recv = recv[1:]

      if not length:
        break

      recv = recv[length:]

    recv = recv[4:]

  for _ in range(response.header.ancount):
    itm = rr()

    while True:
      length = ord(recv[0])

      # An entire domain name or a list of labels at the end of a domain name
      # is replaced with a pointer to a prior occurance of the same name
      if 0xbf < length:
        recv = recv[2:]

        break

      recv = recv[1:]

      if not length:
        break

      recv = recv[length:]

    itm.type = (ord(recv[0]) << 8) + ord(recv[1])
    itm.rdlength = (ord(recv[8]) << 8) + ord(recv[9])

    recv = recv[10:]

    if A == itm.type:

      #   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
      # |                    ADDRESS                    |
      # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

      itm.address = '.'.join(map(untwisted.compose(str, ord), recv[:4]))

      recv = recv[4:]

    elif SRV == itm.type:
      itm.port = (ord(recv[4]) << 8) + ord(recv[5])

      recv = recv[6:]

      itm.target = ''
      while True:
        length = ord(recv[0])

        recv = recv[1:]

        if not length:
          break

        itm.target += recv[:length] + '.'

        recv = recv[length:]

    response.answer.append(itm)

  #return ...
  raise StopIteration(response)
