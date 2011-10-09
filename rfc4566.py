import rfc3986, rfc5234, rfc5322
from qwer import *

# This memo descripes version 0
protoVersion = qwer('v=(?:', rule('rfc5234.DIGIT'), ')+', rule('rfc5234.CRLF'))

# String of visible characters
nonWsString = qwer('(?:', rule('rfc5234.VCHAR'), '|[\x80-\xff])+')

# Pretty side definition, but doesn't include space
username = rule('nonWsString')

# Should be unique for this username/host
sessId = qwer('(?:', rule('rfc5234.DIGIT'), ')+')

sessVersion = qwer('(?:', rule('rfc5234.DIGIT'), ')+')

# Typically "IN"
nettype = rule('token')

# Typically "IP4" or "IP6"
addrtype = rule('token')

hex4 = qwer('(?:', rule('rfc5234.HEXDIG'), '){1,4}')
hexseq = qwer(rule('hex4'), '(?::', rule('hex4'), ')*')
hexpart = qwer('(?:', rule('hexseq'), '|', rule('hexseq'), '::(?:', rule('hexseq'), ')?|::(?:', rule('hexseq'), ')?)')
posDigit = qwer('[1-9]')
decimalUchar = qwer('(?:', rule('rfc5234.DIGIT'), '|', rule('posDigit'), rule('rfc5234.DIGIT'), '|1(?:', rule('rfc5234.DIGIT'), '){2}|2[0-4]', rule('rfc5234.DIGIT'), '|25[0-5])')
b1 = rule('decimalUchar')
ip4Address = qwer(rule('b1'), '(?:\.', rule('decimalUchar'), '){3}')
ip6Address = qwer(rule('hexpart'), '(?::', rule('ip4Address'), ')?')
alphaNumeric = qwer('(?:', rule('rfc5234.ALPHA'), '|', rule('rfc5234.DIGIT'), ')')

# Fully qualified domain name as specified in RFC 1035 (and updates)
fqdn = qwer('(?:', rule('alphaNumeric'), '|-|\.){4,}')

extnAddr = rule('nonWsString')
unicastAddress = qwer('(?:', rule('ip4Address'), '|', rule('ip6Address'), '|', rule('fqdn'), '|', rule('extnAddr'), ')')
originField = qwer('o=', rule('username'), ' ', rule('sessId'), ' ', rule('sessVersion'), ' ', rule('nettype'), ' ', rule('addrtype'), ' ', rule('unicastAddress'), rule('rfc5234.CRLF'))

# Any byte except NUL, CR, or LF
byteString = qwer('[\1-\x09\v\f\x0e-\xff]+')

# Default is to interpret this as UTF-8 text.  ISO 8859-1 requires
# "a=charset:ISO-8859-1" session-level attribute to be used
text = rule('byteString')

sessionNameField = qwer('s=', rule('text'), rule('rfc5234.CRLF'))
uri = rule('rfc3986.uriReference')
uriField = qwer('(?:u=', rule('uri'), rule('rfc5234.CRLF'), ')?')

# Any byte except NUL, CR, LF, or the quoting characters ()<>
emailSafe = qwer('[\1-\x09\v\f\x0e-\'*-;=?-\xff]')

addressAndComment = qwer(rule('rfc5322.addrSpec'), ' +\((?:', rule('emailSafe'), ')+\)')
dispnameAndAddress = qwer('(?:', rule('emailSafe'), ')+ +<', rule('rfc5322.addrSpec'), '>')
emailAddress = qwer('(?:', rule('addressAndComment'), '|', rule('dispnameAndAddress'), '|', rule('rfc5322.addrSpec'), ')')
emailFields = qwer('(?:e=', rule('emailAddress'), rule('rfc5234.CRLF'), ')*')
phone = qwer('\+?', rule('rfc5234.DIGIT'), '(?: |-|', rule('rfc5234.DIGIT'), ')+')
phoneNumber = qwer('(?:', rule('phone'), ' *\((?:', rule('emailSafe'), ')+\)|(?:', rule('emailSafe'), ')+<', rule('phone'), '>|', rule('phone'), ')')
phoneFields = qwer('(?:p=', rule('phoneNumber'), rule('rfc5234.CRLF'), ')*')

# Decimal representation of NTP time in seconds since 1900.  The representation
# of NTP time is an unbounded length field containing at least 10 digits.
# Unlike the 64-bit representation used elsewhere, time in SDP does not wrap in
# the year 2036
time = qwer(rule('posDigit'), '(?:', rule('rfc5234.DIGIT'), '){9,}')

startTime = qwer('(?:', rule('time'), '|0)')
stopTime = qwer('(?:', rule('time'), '|0)')
fixedLenTimeUnit = qwer('[dhms]')
repeatInterval = qwer(rule('posDigit'), '(?:', rule('rfc5234.DIGIT'), ')*(?:', rule('fixedLenTimeUnit'), ')?')
typedTime = qwer('(?:', rule('rfc5234.DIGIT'), ')+(?:', rule('fixedLenTimeUnit'), ')?')
repeatFields = qwer('r=', rule('repeatInterval'), ' ', rule('typedTime'), '(?: ', rule('typedTime'), ')+')
zoneAdjustments = qwer('z=', rule('time'), ' -?', rule('typedTime'), '(?: ', rule('time'), ' -?', rule('typedTime'), ')*')
timeFields = qwer('(?:t=', rule('startTime'), ' ', rule('stopTime'), '(?:', rule('rfc5234.CRLF'), rule('repeatFields'), ')*', rule('rfc5234.CRLF'), ')+(?:', rule('zoneAdjustments'), rule('rfc5234.CRLF'), ')?')
tokenChar = qwer('[!#-\'*+\-.\dA-Z^-~]')
token = qwer('(?:', rule('tokenChar'), ')+')

# Typically "audio", "video", "text", or "application"
media = rule('token')

port = qwer('(?:', rule('rfc5234.DIGIT'), ')+')
integer = qwer(rule('posDigit'), '(?:', rule('rfc5234.DIGIT'), ')*')

# Typically "RTP/AVP" or "udp"
proto = qwer(rule('token'), '(?:/', rule('token'), ')*')

# Typically an RTP payload type for audio and video media
fmt = rule('token')

mediaField = qwer('m=', rule('media'), ' ', rule('port'), '(?:/', rule('integer'), ')? ', rule('proto'), '(?: ', rule('fmt'), ')+', rule('rfc5234.CRLF'))
informationField = qwer('(?:i=', rule('text'), rule('rfc5234.CRLF'), ')?')
m1 = qwer('(?:22[4-9]|23', rule('rfc5234.DIGIT'), ')')
ttl = qwer('(?:', rule('posDigit'), '(?:', rule('rfc5234.DIGIT'), '){,2}|0)')

# IPv4 multicast addresses may be in the range 224.0.0.0 to 239.255.255.255
ip4Multicast = qwer(rule('m1'), '(?:\.', rule('decimalUchar'), '){3}/', rule('ttl'), '(?:/', rule('integer'), ')?')

# IPv6 address starting with FF
ip6Multicast = qwer(rule('hexpart'), '(?:/', rule('integer'), ')?')

multicastAddress = qwer('(?:', rule('ip4Multicast'), '|', rule('ip6Multicast'), '|', rule('fqdn'), '|', rule('extnAddr'), ')')
connectionAddress = qwer('(?:', rule('multicastAddress'), '|', rule('unicastAddress'), ')')

# A connection field must be present in every media description or at the
# session-level
connectionField = qwer('(?:c=', rule('nettype'), ' ', rule('addrtype'), ' ', rule('connectionAddress'), rule('rfc5234.CRLF'), ')?')

bwtype = rule('token')
bandwidth = qwer('(?:', rule('rfc5234.DIGIT'), ')+')
bandwidthFields = qwer('(?:b=', rule('bwtype'), ':', rule('bandwidth'), rule('rfc5234.CRLF'), ')*')
base64Char = qwer('(?:', rule('rfc5234.ALPHA'), '|', rule('rfc5234.DIGIT'), '|\+|/)')
base64Unit = qwer('(?:', rule('base64Char'), '){4}')
base64Pad = qwer('(?:(?:', rule('base64Char'), '){2}==|(?:', rule('base64Char'), '){3}=)')
base64 = qwer('(?:', rule('base64Unit'), '(?:', rule('base64Pad'), ')?)*')
keyType = qwer('(?:prompt|clear:', rule('text'), '|base64:', rule('base64'), '|uri:', rule('uri'), ')')
keyField = qwer('(?:k=', rule('keyType'), rule('rfc5234.CRLF'), ')?')
attValue = rule('byteString')
attField = rule('token')
attribute = qwer('(?:', rule('attField'), ':', rule('attValue'), '|', rule('attField'), ')')
attributeFields = qwer('(?:a=', rule('attribute'), rule('rfc5234.CRLF'), ')*')
mediaDescriptions = qwer('(?:', rule('mediaField'), rule('informationField'), '(?:', rule('connectionField'), ')*', rule('bandwidthFields'), rule('keyField'), rule('attributeFields'), ')*')
sessionDescription = qwer(rule('protoVersion'), rule('originField'), rule('sessionNameField'), rule('informationField'), rule('uriField'), rule('emailFields'), rule('phoneFields'), rule('connectionField'), rule('bandwidthFields'), rule('timeFields'), rule('keyField'), rule('attributeFields'), rule('mediaDescriptions'))
