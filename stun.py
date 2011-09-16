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

#  0 1 2 3 4 5 6 7 8 9 A B C D E F 0 1 2 3 4 5 6 7 8 9 A B C D E F
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# |             Type              |            Length             |
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# |                       Value (variable)                    ...
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

class attribute:
  def __init__(ctx, type, value):
    ctx.type = type
    ctx.value = value

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

  type = ord(recv[20]) << 8 | ord(recv[21])
  length = ord(recv[22]) << 8 | ord(recv[23])

  response.attribute.append(attribute(type, recv[24:24 + length]))

  #return ...
  raise StopIteration(response)
