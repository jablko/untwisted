import rfc5234, rfc5322

letDig = '(?:' + rfc5234.ALPHA + '|' + rfc5234.DIGIT + ')'
ldhStr = '(?:' + rfc5234.ALPHA + '|' + rfc5234.DIGIT + '|-)*' + letDig
subDomain = letDig + '(?:' + ldhStr + ')?'
domain = subDomain + '(?:\.' + subDomain + ')*'
atDomain = '@' + domain

# Note that this form, the so-called "source route", MUST be accepted, SHOULD
# NOT be generated, and SHOULD be ignored
adl = atDomain + '(?:,' + atDomain + ')*'

atom = '(?:' + rfc5322.atext + ')+'
dotString = atom + '(?:\.' + atom + ')*'
qtextSmtp = '[ !#-[\]-~]'
quotedPairSmtp = '\\[ -~]'
qcontentSmtp = '(?:' + qtextSmtp + '|' + quotedPairSmtp + ')'
quotedString = rfc5234.DQUOTE + '(?:' + qcontentSmtp + ')*' + rfc5234.DQUOTE
localPart = '(?:' + dotString + '|' + quotedString + ')'

# Representing a decimal integer value in the range 0 through 255
snum = '(?:' + rfc5234.DIGIT + '){1,3}'

ipv4AddressLiteral = snum + '(?:\.' + snum + '){3}'
ipv6Hex = '(?:' + rfc5234.HEXDIG + '){1,4}'
ipv6Full = ipv6Hex + '(?::' + ipv6Hex + '){7}'

# The "::" represents at least 2 16-bit groups of zeros.  No more than 6 groups
# in addition to the "::" may be present
ipv6Comp = '(?:' + ipv6Hex + '(?::' + ipv6Hex + '){,5})?::(?:' + ipv6Hex + '(?::' + ipv6Hex + '){,5})?'

ipv6v4Full = ipv6Hex + '(?::' + ipv6Hex + '){5}:' + ipv4AddressLiteral

# The "::" represents at least 2 16-bit groups of zeros.  No more than 4 groups
# in addition to the "::" and IPv4-address-literal may be present
ipv6v4Comp = '(?:' + ipv6Hex + '(?::' + ipv6Hex + '){,3})?::(?:' + ipv6Hex + '(?::' + ipv6Hex + '){,3}:)?' + ipv4AddressLiteral

ipv6Addr = '(?:' + ipv6Full + '|' + ipv6Comp + '|' + ipv6v4Full + '|' + ipv6v4Comp + ')'
ipv6AddressLiteral = 'IPv6:' + ipv6Addr

# Standardized-tag MUST be specified in a Standards-Track RFC and registered
# with IANA
standardizedTag = ldhStr

# Printable US-ASCII characters not including "[", "]", or "\"
dcontent = '[!-Z^-~]'

generalAddressLiteral = standardizedTag + ':' + '(?:' + dcontent + ')+'
addressLiteral = '\[(?:' + ipv4AddressLiteral + '|' + ipv6AddressLiteral + '|' + generalAddressLiteral + ')]'
mailbox = localPart + '@(?:' + domain + '|' + addressLiteral + ')'
path = '<(?:' + adl + ':)?(' + mailbox + ')>'
reversePath = '(?:' + path + '|<>)'
esmtpKeyword = '(?:' + rfc5234.ALPHA + '|' + rfc5234.DIGIT + ')(?:' + rfc5234.ALPHA + '|' + rfc5234.DIGIT + '|-)*'

# Any CHAR excluding "=", SP, and control characters.  If this string is an
# email address, i.e. a Mailbox, then the "xtext" syntax SHOULD be used
esmtpValue = '[!-<>-~]+'

esmtpParam = esmtpKeyword + '(?:=' + esmtpValue + ')?'
mailParameters = esmtpParam + '(?: ' + esmtpParam + ')*'

mail = 'MAIL FROM:' + reversePath + '(?:' + mailParameters + ')?' + rfc5234.CRLF

forwardPath = path
rcptParameters = esmtpParam + '(?: ' + esmtpParam + ')*'

rcpt = 'RCPT TO:(?:<Postmaster@' + domain + '>|<Postmaster>|' + forwardPath + ')(?: ' + rcptParameters + ')?' + rfc5234.CRLF

# HT, SP, printable US-ASCII
textstring = '[\t -~]+'

replyCode = '[2-5][0-5][0-9]'

replyLine = '(?:' + replyCode + '-(?:' + textstring + ')?' + rfc5234.CRLF + ')*(' + replyCode + ')(?: (' + textstring + '))?' + rfc5234.CRLF

# Information derived by server from TCP connection not client EHLO
tcpInfo = '(?:' + addressLiteral + '|' + domain + rfc5322.FWS + addressLiteral + ')'

extendedDomain = '(?:' + domain + '|' + domain + rfc5322.FWS + '\(' + tcpInfo + '\)|' + addressLiteral + rfc5322.FWS + '\(' + tcpInfo + '\))'
fromDomain = 'from' + rfc5322.FWS + extendedDomain
byDomain = rfc5322.CFWS + 'by' + rfc5322.FWS + extendedDomain
addtlLink = atom
link = '(?:TCP|' + addtlLink + ')'
via = rfc5322.CFWS + 'via' + rfc5322.FWS + link

# Upstream client authenticated,
# http://thread.gmane.org/gmane.mail.postfix.user/215958
protocol = 'ESMTPA'

With = rfc5322.CFWS + 'with' + rfc5322.FWS + protocol
id = rfc5322.CFWS + 'id' + rfc5322.FWS + '(?:' + atom + '|' + rfc5322.msgId + ')'
For = rfc5322.CFWS + 'for' + rfc5322.FWS + '(?:' + path + '|' + mailbox + ')'
string = '(?:' + atom + '|' + quotedString + ')'

# Additional standard clauses may be added in this location by future standards
# and registered with IANA.  SMTP servers SHOULD NOT use unregistered names
additionalRegisteredClauses = rfc5322.CFWS + atom + rfc5322.FWS + string

optInfo = '(?:' + via + ')?(?:' + With + ')?(?:' + id + ')?(?:' + For + ')?(?:' + additionalRegisteredClauses + ')?'
stamp = fromDomain + byDomain + optInfo + '(?:' + rfc5322.CFWS + ')?;' + rfc5322.FWS + rfc5322.dateTime

timeStampLine = 'Received:' + rfc5322.FWS + stamp + rfc5234.CRLF
