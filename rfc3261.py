import rfc3966, rfc5234
from qwer import *

alphanum = qwer('(?:', rule('rfc5234.ALPHA'), '|', rule('rfc5234.DIGIT'), ')')
mark = qwer('[!\'()*\-._~]')
unreserved = qwer('(?:', rule('alphanum'), '|', rule('mark'), ')')
escaped = qwer('%', rule('rfc5234.HEXDIG'), rule('rfc5234.HEXDIG'))
userUnreserved = qwer('[$&+,/;=?]')
user = qwer('(?:', rule('unreserved'), '|', rule('escaped'), '|', rule('userUnreserved'), ')+')
password = qwer('(?:', rule('unreserved'), '|', rule('escaped'), '|[$&+,=])*')
userinfo = qwer('(?:', rule('user'), '|', rule('rfc3966.telephoneSubscriber'), ')(?::', rule('password'), ')?@')
domainlabel = qwer('(?:', rule('alphanum'), '|', rule('alphanum'), '(?:', rule('alphanum'), '|-)*', rule('alphanum'), ')')
toplabel = qwer('(?:', rule('rfc5234.ALPHA'), '|', rule('rfc5234.ALPHA'), '(?:', rule('alphanum'), '|-)*', rule('alphanum'), ')')
hostname = qwer('(?:', rule('domainlabel'), '\.)*', rule('toplabel'), '\.?')
hex4 = qwer('(?:', rule('rfc5234.HEXDIG'), '){1,4}')
hexseq = qwer(rule('hex4'), '(?::', rule('hex4'), ')*')
hexpart = qwer('(?:', rule('hexseq'), '|', rule('hexseq'), '::(?:', rule('hexseq'), ')?|::(?:', rule('hexseq'), ')?)')
ipv4address = qwer('(?:', rule('rfc5234.DIGIT'), '){1,3}\.(?:', rule('rfc5234.DIGIT'), '){1,3}\.(?:', rule('rfc5234.DIGIT'), '){1,3}\.(?:', rule('rfc5234.DIGIT'), '){1,3}')
ipv6address = qwer(rule('hexpart'), '(?::', rule('ipv4address'), ')?')
ipv6reference = qwer('\[', rule('ipv6address'), ']')
host = qwer('(?:', rule('hostname'), '|', rule('ipv4address'), '|', rule('ipv6reference'), ')')
port = qwer('(?:', rule('rfc5234.DIGIT'), ')+')
hostport = qwer(rule('host'), '(?::', rule('port'), ')?')
token = qwer('(?:', rule('alphanum'), '|[-!%*+\'._`~])+')
otherTransport = rule('token')
transportParam = qwer('transport=(?:udp|tcp|sctp|tls|', rule('otherTransport'), ')')
otherUser = rule('token')
userParam = qwer('user=(?:phone|ip|', rule('otherUser'), ')')
extensionMethod = rule('token')
method = qwer('(?:INVITE|ACK|OPTIONS|BYE|CANCEL|REGISTER|', rule('extensionMethod'), ')')
methodParam = qwer('method=', rule('method'))

# 0 to 255
ttl = qwer('(?:', rule('rfc5234.DIGIT'), '){1,3}')

ttlParam = qwer('ttl=', rule('ttl'))
maddrParam = qwer('maddr=', rule('host'))
lrParam = qwer('lr')
paramUnreserved = qwer('[]$&+/:[]')
paramchar = qwer('(?:', rule('paramUnreserved'), '|', rule('unreserved'), '|', rule('escaped'), ')')
pname = qwer('(?:', rule('paramchar'), ')+')
pvalue = qwer('(?:', rule('paramchar'), ')+')
otherParam = qwer(rule('pname'), '(?:=', rule('pvalue'), ')?')
uriParameter = qwer('(?:', rule('transportParam'), '|', rule('userParam'), '|', rule('methodParam'), '|', rule('ttlParam'), '|', rule('maddrParam'), '|', rule('lrParam'), '|', rule('otherParam'), ')')
uriParameters = qwer('(?:;', rule('uriParameter'), ')*')
hnvUnreserved = qwer('[]$+/:?[]')
hvalue = qwer('(?:', rule('hnvUnreserved'), '|', rule('unreserved'), '|', rule('escaped'), ')*')
hname = qwer('(?:', rule('hnvUnreserved'), '|', rule('unreserved'), '|', rule('escaped'), ')+')
header = qwer(rule('hname'), '=', rule('hvalue'))
headers = qwer('\?', rule('header'), '(?:&', rule('header'), ')*')
sipUri = qwer('sip:(?:', rule('userinfo'), ')?', rule('hostport'), rule('uriParameters'), '(?:', rule('headers'), ')?')
sipsUri = qwer('sips:(?:', rule('userinfo'), ')?', rule('hostport'), rule('uriParameters'), '(?:', rule('headers'), ')?')
scheme = qwer(rule('rfc5234.ALPHA'), '(?:', rule('rfc5234.ALPHA'), '|', rule('rfc5234.DIGIT'), '|[-+.])*')
srvr = qwer('(?:(?:', rule('userinfo'), '@)?', rule('hostport'), ')?')
regName = qwer('(?:', rule('unreserved'), '|', rule('escaped'), '|[$&+,:;=@])+')
authority = qwer('(?:', rule('srvr'), '|', rule('regName'), ')')
pchar = qwer('(?:', rule('unreserved'), '|', rule('escaped'), '|[$&+,:=@])')
param = qwer('(?:', rule('pchar'), ')*')
segment = qwer('(?:', rule('pchar'), ')*(?:;', rule('param'), ')*')
pathSegments = qwer(rule('segment'), '(?:/', rule('segment'), ')*')
absPath = qwer('/', rule('pathSegments'))
netPath = qwer('//', rule('authority'), '(?:', rule('absPath'), ')?')
reserved = qwer('[$&+,/:;=?@]')
uric = qwer('(?:', rule('reserved'), '|', rule('unreserved'), '|', rule('escaped'), ')')
query = qwer('(?:', rule('uric'), ')*')
hierPart = qwer('(?:', rule('netPath'), '|', rule('absPath'), ')(?:\?', rule('query'), ')?')
uricNoSlash = qwer('(?:', rule('unreserved'), '|', rule('escaped'), '|[$&+,:;=?@])')
opaquePart = qwer(rule('uricNoSlash'), '(?:', rule('uric'), ')*')
absoluteUri = qwer(rule('scheme'), ':(?:', rule('hierPart'), '|', rule('opaquePart'), ')')
requestUri = qwer('(?:', rule('sipUri'), '|', rule('sipsUri'), '|', rule('absoluteUri'), ')')
sipVersion = qwer('SIP/(?:', rule('rfc5234.DIGIT'), ')+\.(?:', rule('rfc5234.DIGIT'), ')+')

informational = qwer('(?:100', # Trying
  '|180', # Ringing
  '|181', # Call is being forwarded
  '|182', # Queued
  '|183)') # Session progress

redirection = qwer('(?:300', # Multiple choices
  '|301', # Moved permanently
  '|302', # Moved temporarily
  '|305', # Use proxy
  '|380)') # Alternative service

# OK
success = qwer('200')

clientError = qwer('(?:400', # Bad request
  '|401', # Unauthorized
  '|402', # Payment required
  '|403', # Forbidden
  '|404', # Not found
  '|405', # Method not allowed
  '|406', # Not acceptable
  '|407', # Proxy authentication required
  '|408', # Request timeout
  '|410', # Gone
  '|413', # Request entity too large
  '|414', # Request-URI too large
  '|415', # Unsupported media type
  '|416', # Unsupported URI scheme
  '|420', # Bad extension
  '|421', # Extension too brief
  '|423', # Interval too brief
  '|480', # Temporarily not available
  '|481', # Call leg/transaction does not exist
  '|482', # Loop detected
  '|483', # Too many hops
  '|484', # Address incomplete
  '|485', # Ambiguous
  '|486', # Busy here
  '|487', # Request terminated
  '|488', # Not acceptable here
  '|491', # Request pending
  '|493)') # Undecipherable

serverError = qwer('(?:500', # Internal server error
  '|501', # Not implemented
  '|502', # Bad gateway
  '|503', # Service unavailable
  '|504', # Server time-out
  '|505', # SIP version not supported
  '|513)') # Message too large

globalFailure = qwer('(?:600', # Busy everywhere
  '|603', # Decline
  '|604', # Does not exist anywhere
  '|606)') # Not acceptable

extensionCode = qwer('(?:', rule('rfc5234.DIGIT'), '){3}')
statusCode = qwer('(?:', rule('informational'), '|', rule('redirection'), '|', rule('success'), '|', rule('clientError'), '|', rule('serverError'), '|', rule('globalFailure'), '|', rule('extensionCode'), ')')
utf8Cont = qwer('[\x80-\xbf]')
utf8Nonascii = qwer('(?:[\xc0-\xdf]', rule('utf8Cont'), '|[\xe0-\xef](?:', rule('utf8Cont'), '){2}|[\xf0-\xf7](?:', rule('utf8Cont'), '){3}|[\xf8-\xfb](?:', rule('utf8Cont'), '){4}|[\xfc-\xfd](?:', rule('utf8Cont'), '){5})')
reasonPhrase = qwer('(?:', rule('reserved'), '|', rule('unreserved'), '|', rule('escaped'), '|', rule('utf8Nonascii'), '|', rule('utf8Cont'), '| |\t)*')
statusLine = qwer(rule('sipVersion'), ' ', rule('statusCode'), ' ', rule('reasonPhrase'), rule('rfc5234.CRLF'))
