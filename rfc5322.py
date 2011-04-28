import rfc5234

# Folding white space
FWS = '(?:(?:' + rfc5234.WSP + ')*' + rfc5234.CRLF + ')?(?:' + rfc5234.WSP + ')+'

# Printable US-ASCII characters not including "(", ")", or "\"
ctext = '[!-\'*-[\]-~]'

quotedPair = '\\\(?:' + rfc5234.VCHAR + '|' + rfc5234.WSP + ')'

# Recursive
ccontent = '(?:' + ctext + '|' + quotedPair + ')'

comment = '\((?:(?:' + FWS + ')?' + ccontent + ')*(?:' + FWS + ')?\)'
CFWS = '(?:(?:(?:' + FWS + ')?' + comment + ')+(?:' + FWS + ')?|' + FWS + ')'

# Printable US-ASCII characters not including specials.  Used for atoms
atext = '(?:[!#$%&\'*+\-/=?^_`{|}~]|' + rfc5234.ALPHA + '|' + rfc5234.DIGIT + ')'

atom = '(?:' + CFWS + ')?(?:' + atext + ')+(?:' + CFWS + ')?'

# Printable US-ASCII characters not including "\" or the quote character
qtext = '[!#-[\]-~]'

qcontent = '(?:' + qtext + '|' + quotedPair + ')'
quotedString = '(' + CFWS + ')?' + rfc5234.DQUOTE + '(?:(?:' + FWS + ')?' + qcontent + ')*(?:' + FWS + ')?' + rfc5234.DQUOTE + '(?:' + CFWS + ')?'
word = '(?:' + atom + '|' + quotedString + ')'
phrase = '(?:' + word + ')+'
displayName = phrase
dotAtomText = '(?:' + atext + ')+(?:\.(?:' + atext + ')+)*'
dotAtom = '(' + CFWS + ')?' + dotAtomText + '(' + CFWS + ')?'
localPart = '(?:' + dotAtom + '|' + quotedString + ')'

# Printable US-ASCII characters not including "[", "]", or "\"
dtext = '[!-Z^-~]'

domainLiteral = '(?:' + CFWS + ')?\[(?:(?:' + FWS + ')?' + dtext + ')*(?:' + FWS + ')?](' + CFWS + ')?'
domain = '(?:' + dotAtom + '|' + domainLiteral + ')'
addrSpec = localPart + '@' + domain
angleAddr = '((?:' + CFWS + ')?<)' + addrSpec + '(>(?:' + CFWS + ')?)'
nameAddr = '(' + displayName + ')?' + angleAddr
mailbox = '(?:' + nameAddr + '|' + addrSpec + ')'

From = 'From:' + mailbox + rfc5234.CRLF

idLeft = dotAtomText
noFoldLiteral = '\[(?:' + dtext + ')*]'
idRight = '(?:' + dotAtomText + '|' + noFoldLiteral + ')'
msgId = '(?:' + CFWS + ')?<(' + idLeft + '@' + idRight + ')>(?:' + CFWS + ')?'

inReplyTo = 'In-Reply-To:(?:' + msgId + ')+' + rfc5234.CRLF

references = 'References:(?:' + msgId + ')+' + rfc5234.CRLF

messageId = 'Message-ID:' + msgId + rfc5234.CRLF

dayOfWeek = '(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)'
day = '(?:' + FWS + ')?(?:' + rfc5234.DIGIT + '){1,2}' + FWS
month = '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
year = FWS + '(?:' + rfc5234.DIGIT + '){4,}' + FWS
date = day + month + year
hour = '(?:' + rfc5234.DIGIT + '){2}'
minute = '(?:' + rfc5234.DIGIT + '){2}'
second = '(?:' + rfc5234.DIGIT + '){2}'
timeOfDay = hour + ':' + minute + '(?::' + second + ')?'
zone = FWS + '[+-](?:' + rfc5234.DIGIT + '){4}'
time = timeOfDay + zone
dateTime = '(?:' + dayOfWeek + ',)?' + date + time + '(?:' + CFWS + ')?'
