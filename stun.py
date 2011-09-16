import os, socket, untwisted
from untwisted import promise, udp

binding = 1

# Comprehension-required range (0x0000-0x7FFF)

MAPPED_ADDRESS = 0x1
USERNAME = 0x6
MESSAGE_INTEGRITY = 0x8
ERROR_CODE = 9
UNKNOWN_ATTRIBUTES = 0xa
REALM = 0x14
NONCE = 0x15
XOR_MAPPED_ADDRESS = 0x20

# Comprehension-optional range (0x8000-0xFFFF)

SOFTWARE = 0x8022
ALTERNATE_SERVER = 0x8023
FINGERPRINT = 0x8028

# The address family can take on the following values

IPv4 = 1
IPv6 = 2

#  0 1 2 3 4 5 6 7 8 9 A B C D E F 0 1 2 3 4 5 6 7 8 9 A B C D E F
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# |             Type              |            Length             |
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# |                       Value (variable)                    ...
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

class attribute:
  __metaclass__ = type

  def __init__(ctx, type, value):
    ctx.type = type
    ctx.value = value

  __delitem__ = object.__delattr__
  __getitem__ = object.__getattribute__
  __setitem__ = object.__setattr__

class message:
  def __init__(ctx):
    ctx.attribute = untwisted.oneMany()

  #  0 1 2 3 4 5 6 7 8 9 A B C D E F 0 1 2 3 4 5 6 7 8 9 A B C D E F
  # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
  # |0 0|     STUN Message Type     |        Message Length         |
  # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
  # |                         Magic Cookie                          |
  # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
  # |                                                               |
  # |                   Transaction ID (96 bits)                    |
  # |                                                               |
  # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

  #   2  3  4  5  6  7  8  9  A  B  C  D  E  F
  # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+
  # |MB|MA|M9|M8|M7|C1|M6|M5|M4|C0|M3|M2|M1|M0|
  # +--+--+--+--+--+--+--+--+--+--+--+--+--+--+

  def __str__(ctx):
    message = ''.join(map(str, ctx.attribute))

    return chr(ctx.messageMethod >> 6 & 0xfe | ctx.messageClass >> 8) + chr(ctx.messageMethod << 1 & 0xe0 | ctx.messageClass & 0xff | ctx.messageMethod & 0x0f) + chr(len(message) >> 8) + chr(len(message) & 0xff) + ctx.magicCookie + ctx.transactionId + message

@promise.resume
def request(server, messageMethod=binding):
  try:
    transport = yield udp.connect(server, 'stun')()

  # Avoid error: service/proto not found
  except socket.error:
    transport = yield udp.connect(server, 3478)()

  request = message()

  request.messageMethod = messageMethod
  request.messageClass = 0x0000

  request.magicCookie = '\x21\x12\xa4\x42'
  request.transactionId = os.urandom(12)

  transport.write(str(request))

  recv = yield transport.recv()

  response = message()

  response.messageMethod = ord(recv[0]) << 6 & 0xf800 | ord(recv[1]) >> 1 & 0xf0 | ord(recv[1]) & 0xf
  response.messageClass = ord(recv[0]) << 8 & 0x100 | ord(recv[1]) & 0x10

  response.magicCookie = recv[4:8]
  response.transactionId = recv[8:20]

  recv = recv[20:]

  while recv:
    type = ord(recv[0]) << 8 | ord(recv[1])
    length = ord(recv[2]) << 8 | ord(recv[3])

    itm = attribute(type, recv[4:4 + length])

    # Each STUN attribute MUST end on a 32-bit boundary
    recv = recv[4 + length - length % -4:]

    if type in (MAPPED_ADDRESS, ALTERNATE_SERVER):

      #  0 1 2 3 4 5 6 7 8 9 A B C D E F 0 1 2 3 4 5 6 7 8 9 A B C D E F
      # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      # |0 0 0 0 0 0 0 0|    Family     |             Port              |
      # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      # |                                                               |
      # |                 Address (32 bits or 128 bits)                 |
      # |                                                               |
      # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

      itm.family = ord(itm.value[1])
      itm.port = ord(itm.value[2]) << 8 | ord(itm.value[3])

      if IPv4 == itm.family:
        itm.address = socket.inet_ntop(socket.AF_INET, itm.value[4:])

      elif IPv6 == itm.family:
        itm.address = socket.inet_ntop(socket.AF_INET6, itm.value[4:])

    elif ERROR_CODE == type:

      #  0 1 2 3 4 5 6 7 8 9 A B C D E F 0 1 2 3 4 5 6 7 8 9 A B C D E F
      # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      # |          Reserved, should be 0          |Class|    Number     |
      # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      # |                    Reason Phrase (variable)               ...
      # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

      itm['class'] = ord(itm.value[2])
      itm.number = ord(itm.value[3])
      itm.reasonPhrase = itm.value[4:]

    elif UNKNOWN_ATTRIBUTES == type:

      #  0 1 2 3 4 5 6 7 8 9 A B C D E F 0 1 2 3 4 5 6 7 8 9 A B C D E F
      # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      # |       Attribute 1 Type        |       Attribute 2 Type        |
      # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      # |       Attribute 3 Type        |       Attribute 4 Type    ...
      # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

      itm.attributeType = untwisted.oneMany(*(ord(itm.value[offset]) << 8 | ord(itm.value[offset + 1]) for offset in range(0, len(itm.value), 2)))

    elif XOR_MAPPED_ADDRESS == type:

      #  0 1 2 3 4 5 6 7 8 9 A B C D E F 0 1 2 3 4 5 6 7 8 9 A B C D E F
      # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      # |0 0 0 0 0 0 0 0|    Family     |            X-Port             |
      # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      # |                                                               |
      # |                X-Address (32 bits or 128 bits)                |
      # |                                                               |
      # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

      itm.family = ord(itm.value[1])
      itm.port = (ord(itm.value[2]) ^ ord(response.magicCookie[0])) << 8 | ord(itm.value[3]) ^ ord(response.magicCookie[1])

      if IPv4 == itm.family:
        itm.address = socket.inet_ntop(socket.AF_INET, ''.join(chr(ord(address) ^ ord(magicCookie)) for address, magicCookie in zip(itm.value[4:], response.magicCookie)))

      elif IPv6 == itm.family:
        itm.address = socket.inet_ntop(socket.AF_INET6, ''.join(chr(ord(address) ^ ord(magicCookie)) for address, magicCookie in zip(itm.value[4:], response.magicCookie + response.transactionId)))

    response.attribute.append(itm)

  if 0x0100 != response.messageClass:
    raise response

  #return ...
  raise StopIteration(response)
