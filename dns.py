import re, untwisted
from untwisted import promise, tcp

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
# |                    ADDRESS                    |
# +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

class a:
  def __init__(ctx, read):
    ctx.address = '.'.join(map(untwisted.compose(str, ord), read))

class srv:
  def __init__(ctx, read):
    ctx.port = (ord(read[4]) << 8) + ord(read[5])

    read = read[6:]

    ctx.target = ''
    while True:
      length = ord(read[0])

      read = read[1:]

      if not length:
        break

      ctx.target += read[:length] + '.'

      read = read[length:]

rdata = {
  A: a,
  SRV: srv }

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
def lookup(qname, qtype=A, qclass=IN):
  transport = yield tcp.connect(server[0], 'domain')()

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

  # QR: 0, Opcode: 0, AA: 0, TC: 0, RD: 1, RA: 0, Z: 0, RCODE: 0
  header = '\0\0\1\0\0\1\0\0\0\0\0\0'

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

  question = ''.join((
    ''.join(chr(len(label)) + label for label in qname.split('.')), '\0',
    chr(qtype >> 8), chr(qtype & 0xff),
    chr(qclass >> 8), chr(qclass & 0xff)))

  message = header + question

  # The message is prefixed with a two byte length field which gives the
  # message length, excluding the two byte length field
  transport.write(chr(len(message) >> 8) + chr(len(message) & 0xff) + message)

  read = ''
  while 2 + 12 > len(read):
    read += yield transport.protocol.dataReceived.shift()

  read = read[2 + 12:]
  while not len(read):
    read += yield transport.protocol.dataReceived.shift()

  while True:
    length = ord(read[0])

    # An entire domain name or a list of labels at the end of a domain name is
    # replaced with a pointer to a prior occurance of the same name
    if 0xbf < length:
      while 2 > len(read):
        read += transport.protocol.dataReceived.shift()

      read = read[2:]

      break

    read = read[1:]

    if not length:
      break

    while length > len(read):
      read += yield transport.protocol.dataReceived.shift()

    read = read[length:]

  while 4 > len(read):
    read += yield transport.protocol.dataReceived.shift()

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

  read = read[4:]
  while not len(read):
    read += yield transport.protocol.dataReceived.shift()

  while True:
    length = ord(read[0])

    # An entire domain name or a list of labels at the end of a domain name is
    # replaced with a pointer to a prior occurance of the same name
    if 0xbf < length:
      while 2 > len(read):
        read += transport.protocol.dataReceived.shift()

      read = read[2:]

      break

    read = read[1:]

    if not length:
      break

    while length > len(read):
      read += yield transport.protocol.dataReceived.shift()

    read = read[length:]

  while 10 > len(read):
    read += yield transport.protocol.dataReceived.shift()

  type = (ord(read[0]) << 8) + ord(read[1])
  rdlength = (ord(read[8]) << 8) + ord(read[9])

  read = read[10:]
  while rdlength > len(read):
    read += transport.protocol.dataReceived.shift()

  #return ...
  raise StopIteration(rdata[type](read))
