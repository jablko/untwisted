import rfc2616, rfc3966, rfc5234
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

# Linear whitespace
lws = qwer('(?:(?:', rule('rfc5234.WSP'), ')*', rule('rfc5234.CRLF'), ')?(?:', rule('rfc5234.WSP'), ')+')

# Sep whitespace
sws = qwer('(?:', rule('lws'), ')?')

hcolon = qwer('[ \t]*:', rule('sws'))
ietfToken = rule('token')
xToken = qwer('x-', rule('token'))
extensionToken = qwer('(?:', rule('ietfToken'), '|', rule('xToken'), ')')
discreteType = qwer('(?:text|image|audio|video|application|', rule('extensionToken'), ')')
compositeType = qwer('(?:message|multipart|', rule('extensionToken'), ')')
mType = qwer('(?:', rule('discreteType'), '|', rule('compositeType'), ')')

# Slash
slash = qwer(rule('sws'), '/', rule('sws'))

ianaToken = rule('token')
mSubtype = qwer('(?:', rule('extensionToken'), '|', rule('ianaToken'), ')')

# Semicolon
semi = qwer(rule('sws'), ';', rule('sws'))

mAttribute = rule('token')

# Equal
equal = qwer(rule('sws'), '=', rule('sws'))
qdtext = qwer('(?:', rule('lws'), '|[!#-[\]-~]|', rule('utf8Nonascii'), ')')
quotedPair = qwer('\\[\0-\t\v\f\x0e-\x7f]')
quotedString = qwer(rule('sws'), rule('rfc5234.DQUOTE'), '(?:', rule('qdtext'), '|', rule('quotedPair'), ')*', rule('rfc5234.DQUOTE'))
mValue = qwer('(?:', rule('token'), '|', rule('quotedString'), ')')
mParameter = qwer(rule('mAttribute'), rule('equal'), rule('mValue'))
mediaRange = qwer('(?:\*/\*|', rule('mType'), rule('slash'), '\*|', rule('mType'), rule('slash'), rule('mSubtype'), ')(?:', rule('semi'), rule('mParameter'), ')*')
qvalue = qwer('(?:0(?:\.(?:', rule('rfc5234.DIGIT'), '){,3})?|1(?:\.0{,3})?)')
genValue = qwer('(?:', rule('token'), '|', rule('host'), '|', rule('quotedString'), ')')
genericParam = qwer(rule('token'), '(?:', rule('equal'), rule('genValue'), ')?')
acceptParam = qwer('(?:q', rule('equal'), rule('qvalue'), '|', rule('genericParam'), ')')
acceptRange = qwer(rule('mediaRange'), '(?:', rule('semi'), rule('acceptParam'), ')*')

# Comma
comma = qwer(rule('sws'), ',', rule('sws'))

accept = qwer('Accept', rule('hcolon'), '(?:', rule('acceptRange'), '(?:', rule('comma'), rule('acceptRange'), ')*)?')
contentCoding = rule('token')
codings = qwer('(?:', rule('contentCoding'), '|\*)')
encoding = qwer(rule('codings'), '(?:', rule('semi'), rule('acceptParam'), ')*')
acceptEncoding = qwer('Accept-Encoding', rule('hcolon'), '(?:', rule('encoding'), '(?:', rule('comma'), rule('encoding'), ')*)?')
languageRange = qwer('(?:', rule('rfc5234.ALPHA'), '{1,8}(?:-(?:', rule('rfc5234.ALPHA'), '){1,8})?|\*)')
language = qwer(rule('languageRange'), '(?:', rule('semi'), rule('acceptParam'), ')*')
acceptLanguage = qwer('Accept-Language', rule('hcolon'), '(?:', rule('language'), '(?:', rule('comma'), rule('language'), ')*)?')

# Left angle quote
laquot = qwer(rule('sws'), '<')

# Right angle quote
raquot = qwer('>', rule('sws'))

alertParam = qwer(rule('laquot'), rule('absoluteUri'), rule('raquot'), '(?:', rule('semi'), rule('genericParam'), ')*')
alertInfo = qwer('Alert-Info', rule('hcolon'), rule('alertParam'), '(?:', rule('comma'), rule('alertParam'), ')*')
allow = qwer('Allow', rule('hcolon'), '(?:', rule('method'), '(?:', rule('comma'), rule('method'), ')*)?')
nonceValue = rule('quotedString')
nextnonce = qwer('nextnonce', rule('equal'), rule('nonceValue'))
qopValue = qwer('(?:auth|auth-int|', rule('token'), ')')
messageQop = qwer('qop', rule('equal'), rule('qopValue'))

# Open double quotation mark
ldquot = qwer(rule('sws'), rule('rfc5234.DQUOTE'))

# Lowercase a-f
lhex = qwer('(?:', rule('rfc5234.DIGIT'), '|[a-f])')

# Close double quotation mark
rdquot = qwer(rule('rfc5234.DQUOTE'), rule('sws'))

responseDigest = qwer(rule('ldquot'), '(?:', rule('lhex'), ')*', rule('rdquot'))
responseAuth = qwer('rspauth', rule('equal'), rule('responseDigest'))
cnonceValue = rule('nonceValue')
cnonce = qwer('cnonce', rule('equal'), rule('cnonceValue'))
ncValue = qwer('(?:', rule('lhex'), '){8}')
nonceCount = qwer('nc', rule('equal'), rule('ncValue'))
ainfo = qwer('(?:', rule('nextnonce'), '|', rule('messageQop'), '|', rule('responseAuth'), '|', rule('cnonce'), '|', rule('nonceCount'), ')')
authenticationInfo = qwer('Authenication-Info', rule('hcolon'), rule('ainfo'), '(?:', rule('comma'), rule('ainfo'), ')*')
usernameValue = rule('quotedString')
username = qwer('username', rule('equal'), rule('usernameValue'))
realmValue = rule('quotedString')
realm = qwer('realm', rule('equal'), rule('realmValue'))
nonce = qwer('nonce', rule('equal'), rule('nonceValue'))
digestUriValue = rule('rfc2616.requestUri')
digestUri = qwer('uri', rule('equal'), rule('ldquot'), rule('digestUriValue'), rule('rdquot'))
requestDigest = qwer(rule('ldquot'), '(?:', rule('lhex'), '){32}', rule('rdquot'))
dresponse = qwer('response', rule('equal'), rule('requestDigest'))
algorithm = qwer('algorithm', rule('equal'), '(?:MD5|MD5-sess|', rule('token'), ')')
opaque = qwer('opaque', rule('equal'), rule('quotedString'))
authParamName = rule('token')
authParam = qwer(rule('authParamName'), rule('equal'), '(?:', rule('token'), '|', rule('quotedString'), ')')
digResp = qwer('(?:', rule('username'), '|', rule('realm'), '|', rule('nonce'), '|', rule('digestUri'), '|', rule('dresponse'), '|', rule('algorithm'), '|', rule('cnonce'), '|', rule('opaque'), '|', rule('messageQop'), '|', rule('nonceCount'), '|', rule('authParam'), ')')
digestResponse = qwer(rule('digResp'), '(?:', rule('comma'), rule('digResp'), ')*')
otherResponse = qwer(rule('authScheme'), rule('lws'), rule('authParam'), '(?:', rule('comma'), rule('authParam'), ')*')
credentials = qwer('(?:Digest', rule('lws'), rule('digestResponse'), '|', rule('otherResponse'), ')')
authorization = qwer('Authorization', rule('hcolon'), rule('credentials'))
word = qwer('(?:', rule('alphanum'), '|[!"%\'()*+\-./:<>?[\\\]_`{~}])')
callid = qwer(rule('word'), '(?:@', rule('word'), ')?')
callId = qwer('(?:Call-ID|i)', rule('hcolon'), rule('callid'))
infoParam = qwer('(?:purpose', rule('equal'), '(?:icon|info|card|', rule('token'), ')|', rule('genericParam'), ')')
info = qwer(rule('laquot'), rule('absoluteUri'), rule('raquot'), '(?:', rule('semi'), rule('infoParam'), ')*')
callInfo = qwer('Call-Info', rule('hcolon'), rule('info'), '(?:', rule('comma'), rule('info'), ')*')

# Asterisk
star = qwer(rule('sws'), '\*', rule('sws'))

displayName = qwer('(?:(?:', rule('token'), rule('lws'), ')*|', rule('quotedString'), ')')
addrSpec = qwer('(?:', rule('sipUri'), '|', rule('sipsUri'), '|', rule('absoluteUri'), ')')
nameAddr = qwer('(?:', rule('displayName'), ')?', rule('laquot'), rule('addrSpec'), rule('raquot'))
cpq = qwer('q', rule('equal'), rule('qvalue'))
deltaSeconds = qwer('(?:', rule('rfc5234.DIGIT'), ')+')
cpExpires = qwer('expires', rule('equal'), rule('deltaSeconds'))
contactExtension = rule('genericParam')
contactParams = qwer('(?:', rule('cpq'), '|', rule('cpExpires'), '|', rule('contactExtension'), ')')
contactParam = qwer('(?:', rule('nameAddr'), '|', rule('addrSpec'), ')(?:', rule('semi'), rule('contactParams'), ')*')
contact = qwer('(?:Contact|m)', rule('hcolon'), '(?:', rule('star'), '|', rule('contactParam'), '(?:', rule('comma'), rule('contactParam'), ')*)')
dispExtensionToken = rule('token')
dispType = qwer('(?:render|session|icon|alert|', rule('dispExtensionToken'), ')')
otherHandling = rule('token')
handlingParam = qwer('handling', rule('equal'), '(?:optional|required|', rule('otherHandling'), ')')
dispParam = qwer('(?:', rule('handlingParam'), '|', rule('genericParam'), ')')
contentDisposition = qwer('Content-Disposition', rule('hcolon'), rule('dispType'), '(?:', rule('semi'), rule('dispParam'), ')*')
contentEncoding = qwer('(?:Content-Encoding|e)', rule('hcolon'), rule('contentCoding'), '(?:', rule('comma'), rule('contentCoding'), ')*')
subtag = qwer('(?:', rule('rfc5234.ALPHA'), '){1,8}')
primaryTag = qwer('(?:', rule('rfc5234.ALPHA'), '){1,8}')
languageTag = qwer(rule('primaryTag'), '(?:-', rule('subtag'), ')*')
contentLanguage = qwer('Content-Language', rule('hcolon'), rule('languageTag'), '(?:', rule('comma'), rule('languageTag'), ')*')
contentLength = qwer('(?:Content-Length|l)', rule('hcolon'), '(?:', rule('rfc5234.DIGIT'), ')+')
mediaType = qwer(rule('mType'), rule('slash'), rule('mSubtype'), '(?:', rule('semi'), rule('mParameter'), ')*')
contentType = qwer('(?:Content-Type|c)', rule('hcolon'), rule('mediaType'))
cseq = qwer('CSeq', rule('hcolon'), '(?:', rule('rfc5234.DIGIT'), ')+', rule('lws'), rule('method'))
wkday = qwer('(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)')
month = qwer('(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)')

# day month year (e.g. 02 Jun 1982)
date1 = qwer('(?:', rule('rfc5234.DIGIT'), '){2} ', rule('month'), ' (?:', rule('rfc5234.DIGIT'), '){4}')

# 00:00:00 - 23:59:59
time = qwer('(?:', rule('rfc5234.DIGIT'), '){2}:(?:', rule('rfc5234.DIGIT'), '){2}:(?:', rule('rfc5234.DIGIT'), '){2}')

rfc1123Date = qwer(rule('wkday'), ', ', rule('date1'), ' ', rule('time'), ' GMT')
sipDate = rule('rfc1123Date')
date = qwer('Date', rule('hcolon'), rule('sipDate'))
errorUri = qwer(rule('laquot'), rule('absoluteUri'), rule('raquot'), '(?:', rule('semi'), rule('genericParam'), ')*')
errorInfo = qwer('Error-Info', rule('hcolon'), rule('errorUri'), '(?:', rule('comma'), rule('errorUri'), ')*')
expires = qwer('Expires', rule('hcolon'), rule('deltaSeconds'))
tagParam = qwer('tag', rule('equal'), rule('token'))
fromParam = qwer('(?:', rule('tagParam'), '|', rule('genericParam'), ')')
fromSpec = qwer('(?:', rule('nameAddr'), '|', rule('addrSpec'), ')(?:', rule('semi'), rule('fromParam'), ')*')
From = qwer('(?:From|f)', rule('hcolon'), rule('fromSpec'))
inReplyTo = qwer('In-Reply-To', rule('hcolon'), rule('callid'), '(?:', rule('comma'), rule('callid'), ')*')
maxForwards = qwer('Max-Forwards', rule('hcolon'), '(?:', rule('rfc5234.DIGIT'), ')+')
mimeVersion = qwer('MIME-Version', rule('hcolon'), '(?:', rule('rfc5234.DIGIT'), ')+\.(?:', rule('rfc5234.DIGIT'), ')+')
minExpires = qwer('Min-Expires', rule('hcolon'), rule('deltaSeconds'))
textUtf8char = qwer('(?:[!-~]|', rule('utf8Nonascii'), ')')
textUtf8Trim = qwer('(?:', rule('textUtf8char'), ')+(?:(?:', rule('lws'), ')*', rule('textUtf8char'), ')*')
organization = qwer('Organization', rule('hcolon'), '(?:', rule('textUtf8Trim'), ')?')
otherPriority = rule('token')
priorityValue = qwer('(?:emergency|urgent|normal|non-urgent|', rule('otherPriority'), ')')
priority = qwer('Priority', rule('hcolon'), rule('priorityValue'))
uri = qwer('(?:', rule('absoluteUri'), '|', rule('absPath'), ')')
domain = qwer('domain', rule('equal'), rule('ldquot'), rule('uri'), '(?: +', rule('uri'), ')*', rule('rdquot'))
stale = qwer('stale', rule('equal'), '(?:true|false)')
qopOptions = qwer('qop', rule('equal'), rule('ldquot'), rule('qopValue'), '(?:,', rule('qopValue'), ')*', rule('rdquot'))
digestCln = qwer('(?:', rule('realm'), '|', rule('domain'), '|', rule('nonce'), '|', rule('opaque'), '|', rule('stale'), '|', rule('algorithm'), '|', rule('qopOptions'), '|', rule('authParam'), ')')
authScheme = rule('token')
otherChallenge = qwer(rule('authScheme'), rule('lws'), rule('authParam'), '(?:', rule('comma'), rule('authParam'), ')*')
challenge = qwer('(?:Digest', rule('lws'), rule('digestCln'), '(?:', rule('comma'), rule('digestCln'), ')*|', rule('otherChallenge'), ')')
proxyAuthenticate = qwer('Proxy-Authenticate', rule('hcolon'), rule('challenge'))
proxyAuthorization = qwer('Proxy-Authorization', rule('hcolon'), rule('credentials'))
optionTag = rule('token')
proxyRequire = qwer('Proxy-Require', rule('hcolon'), rule('optionTag'), '(?:', rule('comma'), rule('optionTag'), ')*')
rplytoSpec = qwer('(?:', rule('nameAddr'), '|', rule('addrSpec'), ')')
replyTo = qwer('Reply-To', rule('hcolon'), rule('rplytoSpec'))
require = qwer('Require', rule('hcolon'), rule('optionTag'), '(?:', rule('comma'), rule('optionTag'), ')*')
retryParam = qwer('(?:duration', rule('equal'), rule('deltaSeconds'), '|', rule('genericParam'), ')')
retryAfter = qwer('Retry-After', rule('hcolon'), rule('deltaSeconds'), '(?:', rule('comment'), ')?(?:', rule('semi'), rule('retryParam'), ')*')
rrParam = rule('genericParam')
routeParam = qwer(rule('nameAddr'), '(?:', rule('semi'), rule('rrParam'), ')*')
route = qwer('Route', rule('hcolon'), rule('routeParam'), '(?:', rule('comma'), rule('routeParam'), ')*')
productVersion = rule('token')
product = qwer(rule('token'), '(?:', rule('slash'), rule('productVersion'), ')?')

# Left parenthesis
lparen = qwer(rule('sws'), '\(', rule('sws'))

ctext = qwer('(?:[!-\'*-[\]-~]|', rule('utf8Nonascii'), '|', rule('lws'), ')')

# Right parenthesis
rparen = qwer(rule('sws'), '\)', rule('sws'))

# Recursive
comment = qwer(rule('lparen'), '(?:', rule('ctext'), '|', rule('quotedPair'), ')*', rule('rparen'))

serverVal = qwer('(?:', rule('product'), '|', rule('comment'), ')')
server = qwer('Server', rule('hcolon'), rule('serverVal'), '(?:', rule('lws'), rule('serverVal'), ')*')
subject = qwer('(?:Subject|s)', rule('hcolon'), '(?:', rule('textUtf8Trim'), ')?')
supported = qwer('(?:Supported|k)', rule('hcolon'), '(?:', rule('optionTag'), '(?:', rule('comma'), rule('optionTag'), ')*)?')
delay = qwer('(?:', rule('rfc5234.DIGIT'), ')*(?:\.(?:', rule('rfc5234.DIGIT'), ')*)?')
timestamp = qwer('Timestamp', rule('hcolon'), '(?:', rule('rfc5234.DIGIT'), ')+(?:\.(?:', rule('rfc5234.DIGIT'), ')*)?(?:', rule('lws'), rule('delay'), ')?')
toParam = qwer('(?:', rule('tagParam'), '|', rule('genericParam'), ')')
to = qwer('(?:To|t)', rule('hcolon'), '(?:', rule('nameAddr'), '|', rule('addrSpec'), ')(?:', rule('semi'), rule('toParam'), ')*')
unsupported = qwer('Unsupported', rule('hcolon'), rule('optionTag'), '(?:', rule('comma'), rule('optionTag'), ')*')
userAgent = qwer('User-Agent', rule('hcolon'), rule('serverVal'), '(?:', rule('lws'), rule('serverVal'), ')*')
protocolName = qwer('(?:SIP|', rule('token'), ')')
protocolVersion = rule('token')
transport = qwer('(?:UDP|TCP|TLS|SCTP|', rule('otherTransport'), ')')
sentProtocol = qwer(rule('protocolName'), rule('slash'), rule('protocolVersion'), rule('slash'), rule('transport'))

# Colon
colon = qwer(rule('sws'), ':', rule('sws'))

sentBy = qwer(rule('host'), '(?:', rule('colon'), rule('port'), ')?')
viaTtl = qwer('ttl', rule('equal'), rule('ttl'))
viaMaddr = qwer('maddr', rule('equal'), rule('host'))
viaReceived = qwer('received', rule('equal'), '(?:', rule('ipv4address'), '|', rule('ipv6address'), ')')
viaBranch = qwer('branch', rule('equal'), rule('token'))
viaExtension = rule('genericParam')
viaParams = qwer('(?:', rule('viaTtl'), '|', rule('viaMaddr'), '|', rule('viaReceived'), '|', rule('viaBranch'), '|', rule('viaExtension'), ')')
viaParm = qwer(rule('sentProtocol'), rule('lws'), rule('sentBy'), '(?:', rule('semi'), rule('viaParams'), ')*')
via = qwer('(?:Via|v)', rule('hcolon'), rule('viaParm'), '(?:', rule('comma'), rule('viaParm'), ')*')
warnCode = qwer('(?:', rule('rfc5234.DIGIT'), '){3}')
pseudonym = rule('token')

# The name or pseudonym of the server adding the Warning header, for use in
# debugging
warnAgent = qwer('(?:', rule('hostport'), '|', rule('pseudonym'), ')')

warnText = rule('quotedString')
warningValue = qwer(rule('warnCode'), ' ', rule('warnAgent'), ' ', rule('warnText'))
warning = qwer('Warning', rule('hcolon'), rule('warningValue'), '(?:', rule('comma'), rule('warningValue'), ')*')
wwwAuthenticate = qwer('WWW-Authenticate', rule('hcolon'), rule('challenge'))
headerName = rule('token')
headerValue = qwer('(?:', rule('textUtf8char'), '|', rule('utf8Cont'), '|', rule('lws'), ')*')
extensionHeader = qwer(rule('headerName'), rule('hcolon'), rule('headerValue'))
messageHeader = qwer('(?:', rule('accept'), '|', rule('acceptEncoding'), '|', rule('acceptLanguage'), '|', rule('alertInfo'), '|', rule('allow'), '|', rule('authenticationInfo'), '|', rule('authorization'), '|', rule('callId'), '|', rule('callInfo'), '|', rule('contact'), '|', rule('contentDisposition'), '|', rule('contentEncoding'), '|', rule('contentLanguage'), '|', rule('contentLength'), '|', rule('contentType'), '|', rule('cseq'), '|', rule('date'), '|', rule('errorInfo'), '|', rule('expires'), '|', rule('From'), '|', rule('inReplyTo'), '|', rule('maxForwards'), '|', rule('mimeVersion'), '|', rule('minExpires'), '|', rule('organization'), '|', rule('priority'), '|', rule('proxyAuthenticate'), '|', rule('proxyAuthorization'), '|', rule('proxyRequire'), '|', rule('replyTo'), '|', rule('require'), '|', rule('retryAfter'), '|', rule('route'), '|', rule('server'), '|', rule('subject'), '|', rule('supported'), '|', rule('timestamp'), '|', rule('to'), '|', rule('unsupported'), '|', rule('userAgent'), '|', rule('via'), '|', rule('warning'), '|', rule('wwwAuthenticate'), '|', rule('extensionHeader'), ')', rule('rfc5234.CRLF'))
messageBody = qwer('(?:', rule('rfc5234.OCTET'), ')*')
response = qwer(rule('statusLine'), '(?:', rule('messageHeader'), ')*', rule('rfc5234.CRLF'), rule('messageBody'))
