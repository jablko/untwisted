import rfc5234, rfc5322
from qwer import *

letDig = qwer('(?:', rule('rfc5234.ALPHA'), '|', rule('rfc5234.DIGIT'), ')')
ldhStr = qwer('(?:', rule('rfc5234.ALPHA'), '|', rule('rfc5234.DIGIT'), '|-)*', rule('letDig'))
subDomain = qwer(rule('letDig'), '(?:', rule('ldhStr'), ')?')
domain = qwer(rule('subDomain'), '(?:\.', rule('subDomain'), ')*')

# Representing a decimal integer value in the range 0 through 255
snum = qwer('(?:', rule('rfc5234.DIGIT'), '){1,3}')

ipv4AddressLiteral = qwer(rule('snum'), '(?:\.', rule('snum'), '){3}')
ipv6Hex = qwer('(?:', rule('rfc5234.HEXDIG'), '){1,4}')
ipv6Full = qwer(rule('ipv6Hex'), '(?::', rule('ipv6Hex'), '){7}')

# The "::" represents at least 2 16-bit groups of zeros.  No more than 6 groups
# in addition to the "::" may be present
ipv6Comp = qwer('(?:', rule('ipv6Hex'), '(?::', rule('ipv6Hex'), '){,5})?::(?:', rule('ipv6Hex'), '(?::', rule('ipv6Hex'), '){,5})?')

ipv6v4Full = qwer(rule('ipv6Hex'), '(?::', rule('ipv6Hex'), '){5}:', rule('ipv4AddressLiteral'))

# The "::" represents at least 2 16-bit groups of zeros.  No more than 4 groups
# in addition to the "::" and IPv4-address-literal may be present
ipv6v4Comp = qwer('(?:', rule('ipv6Hex'), '(?::', rule('ipv6Hex'), '){,3})?::(?:', rule('ipv6Hex'), '(?::', rule('ipv6Hex'), '){,3}:)?', rule('ipv4AddressLiteral'))

ipv6Addr = qwer('(?:', rule('ipv6Full'), '|', rule('ipv6Comp'), '|', rule('ipv6v4Full'), '|', rule('ipv6v4Comp'), ')')
ipv6AddressLiteral = qwer('IPv6:', rule('ipv6Addr'))

# Standardized-tag MUST be specified in a Standards-Track RFC and registered
# with IANA
standardizedTag = rule('ldhStr')

# Printable US-ASCII characters not including "[", "]", or "\"
dcontent = qwer('[!-Z^-~]')

generalAddressLiteral = qwer(rule('standardizedTag'), ':', '(?:', rule('dcontent'), ')+')
addressLiteral = qwer('\[(?:', rule('ipv4AddressLiteral'), '|', rule('ipv6AddressLiteral'), '|', rule('generalAddressLiteral'), ')]')

ehlo = qwer('EHLO (?:', rule('domain'), '|', rule('addressLiteral'), ')', rule('rfc5234.CRLF'))

atDomain = qwer('@', rule('domain'))

# Note that this form, the so-called "source route", MUST be accepted, SHOULD
# NOT be generated, and SHOULD be ignored
adl = qwer(rule('atDomain'), '(?:,', rule('atDomain'), ')*')

atom = qwer('(?:', rule('rfc5322.atext'), ')+')
dotString = qwer(rule('atom'), '(?:\.', rule('atom'), ')*')
qtextSmtp = qwer('[ !#-[\]-~]')
quotedPairSmtp = qwer('\\[ -~]')
qcontentSmtp = qwer('(?:', rule('qtextSmtp'), '|', rule('quotedPairSmtp'), ')')
quotedString = qwer(rule('rfc5234.DQUOTE'), '(?:', rule('qcontentSmtp'), ')*', rule('rfc5234.DQUOTE'))
localPart = qwer('(?:', rule('dotString'), '|', rule('quotedString'), ')')
mailbox = qwer(rule('localPart'), '@(?:', rule('domain'), '|', rule('addressLiteral'), ')')
path = qwer('<(?:', rule('adl'), ':)?', rule('mailbox'), '>')
reversePath = qwer('(?:', rule('path'), '|<>)')
esmtpKeyword = qwer('(?:', rule('rfc5234.ALPHA'), '|', rule('rfc5234.DIGIT'), ')(?:', rule('rfc5234.ALPHA'), '|', rule('rfc5234.DIGIT'), '|-)*')

# Any CHAR excluding "=", SP, and control characters.  If this string is an
# email address, i.e. a Mailbox, then the "xtext" syntax SHOULD be used
esmtpValue = qwer('[!-<>-~]+')

esmtpParam = qwer(rule('esmtpKeyword'), '(?:=', rule('esmtpValue'), ')?')
mailParameters = qwer(rule('esmtpParam'), '(?: ', rule('esmtpParam'), ')*')

mail = qwer('MAIL FROM:', rule('reversePath'), '(?:', rule('mailParameters'), ')?', rule('rfc5234.CRLF'))

forwardPath = rule('path')
rcptParameters = qwer(rule('esmtpParam'), '(?: ', rule('esmtpParam'), ')*')

rcpt = qwer('RCPT TO:(?:<Postmaster@', rule('domain'), '>|<Postmaster>|', rule('forwardPath'), ')(?: ', rule('rcptParameters'), ')?', rule('rfc5234.CRLF'))

# HT, SP, printable US-ASCII
textstring = qwer('[\t -~]+')

replyCode = qwer('[2-5][0-5]\d')

replyLine = qwer('(?:', rule('replyCode'), '-(?:', rule('textstring'), ')?', rule('rfc5234.CRLF'), ')*', rule('replyCode'), '(?: ', rule('textstring'), ')?', rule('rfc5234.CRLF'))

# Information derived by server from TCP connection not client EHLO
tcpInfo = qwer('(?:', rule('addressLiteral'), '|', rule('domain'), rule('rfc5322.FWS'), rule('addressLiteral'), ')')

extendedDomain = qwer('(?:', rule('domain'), '|', rule('domain'), rule('rfc5322.FWS'), '\(', rule('tcpInfo'), '\)|', rule('addressLiteral'), rule('rfc5322.FWS'), '\(', rule('tcpInfo'), '\))')
fromDomain = qwer('from', rule('rfc5322.FWS'), rule('extendedDomain'))
byDomain = qwer(rule('rfc5322.CFWS'), 'by', rule('rfc5322.FWS'), rule('extendedDomain'))
addtlLink = rule('atom')
link = qwer('(?:TCP|', rule('addtlLink'), ')')
via = qwer(rule('rfc5322.CFWS'), 'via', rule('rfc5322.FWS'), rule('link'))

# Additional standard names for protocols are registered with the Internet
# Assigned Numbers Authority (IANA) in the "mail parameters" registry.  SMTP
# servers SHOULD NOT use unregistered names
attdlProtocol = rule('atom')

protocol = qwer('(?:ESMTP|SMTP|', rule('attdlProtocol'), ')')
With = qwer(rule('rfc5322.CFWS'), 'with', rule('rfc5322.FWS'), rule('protocol'))
id = qwer(rule('rfc5322.CFWS'), 'id', rule('rfc5322.FWS'), '(?:', rule('atom'), '|', rule('rfc5322.msgId'), ')')
For = qwer(rule('rfc5322.CFWS'), 'for', rule('rfc5322.FWS'), '(?:', rule('path'), '|', rule('mailbox'), ')')
string = qwer('(?:', rule('atom'), '|', rule('quotedString'), ')')

# Additional standard clauses may be added in this location by future standards
# and registered with IANA.  SMTP servers SHOULD NOT use unregistered names
additionalRegisteredClauses = qwer(rule('rfc5322.CFWS'), rule('atom'), rule('rfc5322.FWS'), rule('string'))

optInfo = qwer('(?:', rule('via'), ')?(?:', rule('With'), ')?(?:', rule('id'), ')?(?:', rule('For'), ')?(?:', rule('additionalRegisteredClauses'), ')?')
stamp = qwer(rule('fromDomain'), rule('byDomain'), rule('optInfo'), '(?:', rule('rfc5322.CFWS'), ')?;', rule('rfc5322.FWS'), rule('rfc5322.dateTime'))

timeStampLine = qwer('Received:', rule('rfc5322.FWS'), rule('stamp'), rule('rfc5234.CRLF'))
