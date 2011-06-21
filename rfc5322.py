import rfc5234
from qwer import *

# Folding white space
FWS = qwer('(?:(?:', rule('rfc5234.WSP'), ')*', rule('rfc5234.CRLF'), ')?(?:', rule('rfc5234.WSP'), ')+')

# Printable US-ASCII characters not including "(", ")", or "\"
ctext = qwer('[!-\'*-[\]-~]')

quotedPair = qwer('\\\(?:', rule('rfc5234.VCHAR'), '|', rule('rfc5234.WSP'), ')')

# Recursive
ccontent = qwer('(?:', rule('ctext'), '|', rule('quotedPair'), ')')

comment = qwer('\((?:(?:', rule('FWS'), ')?', rule('ccontent'), ')*(?:', rule('FWS'), ')?\)')
CFWS = qwer('(?:(?:(?:', rule('FWS'), ')?', rule('comment'), ')+(?:', rule('FWS'), ')?|', rule('FWS'), ')')

# Printable US-ASCII characters not including specials.  Used for atoms
atext = qwer('(?:[!#$%&\'*+\-/=?^_`{|}~]|', rule('rfc5234.ALPHA'), '|', rule('rfc5234.DIGIT'), ')')

atom = qwer('(?:', rule('CFWS'), ')?(?:', rule('atext'), ')+(?:', rule('CFWS'), ')?')

# Printable US-ASCII characters not including "\" or the quote character
qtext = qwer('[!#-[\]-~]')

qcontent = qwer('(?:', rule('qtext'), '|', rule('quotedPair'), ')')
quotedString = qwer('(', rule('CFWS'), ')?', rule('rfc5234.DQUOTE'), '(?:(?:', rule('FWS'), ')?', rule('qcontent'), ')*(?:', rule('FWS'), ')?', rule('rfc5234.DQUOTE'), '(?:', rule('CFWS'), ')?')
word = qwer('(?:', rule('atom'), '|', rule('quotedString'), ')')
phrase = qwer('(?:', rule('word'), ')+')
displayName = rule('phrase')
dotAtomText = qwer('(?:', rule('atext'), ')+(?:\.(?:', rule('atext'), ')+)*')
dotAtom = qwer('(', rule('CFWS'), ')?', rule('dotAtomText'), '(', rule('CFWS'), ')?')
localPart = qwer('(?:', rule('dotAtom'), '|', rule('quotedString'), ')')

# Printable US-ASCII characters not including "[", "]", or "\"
dtext = qwer('[!-Z^-~]')

domainLiteral = qwer('(?:', rule('CFWS'), ')?\[(?:(?:', rule('FWS'), ')?', rule('dtext'), ')*(?:', rule('FWS'), ')?](', rule('CFWS'), ')?')
domain = qwer('(?:', rule('dotAtom'), '|', rule('domainLiteral'), ')')
addrSpec = qwer(rule('localPart'), '@', rule('domain'))
angleAddr = qwer('((?:', rule('CFWS'), ')?<)', rule('addrSpec'), '(>(?:', rule('CFWS'), ')?)')
nameAddr = qwer('(', rule('displayName'), ')?', rule('angleAddr'))
mailbox = qwer('(?:', rule('nameAddr'), '|', rule('addrSpec'), ')')

From = qwer('From:', rule('mailbox'), rule('rfc5234.CRLF'))

idLeft = rule('dotAtomText')
noFoldLiteral = qwer('\[(?:', rule('dtext'), ')*]')
idRight = qwer('(?:', rule('dotAtomText'), '|', rule('noFoldLiteral'), ')')
msgId = qwer('(?:', rule('CFWS'), ')?<', rule('idLeft'), '@', rule('idRight'), '>(?:', rule('CFWS'), ')?')

inReplyTo = qwer('In-Reply-To:(?:', rule('msgId'), ')+', rule('rfc5234.CRLF'))

references = qwer('References:(?:', rule('msgId'), ')+', rule('rfc5234.CRLF'))

messageId = qwer('Message-ID:', rule('msgId'), rule('rfc5234.CRLF'))

dayOfWeek = qwer('(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)')
day = qwer('(?:', rule('FWS'), ')?(?:', rule('rfc5234.DIGIT'), '){1,2}', rule('FWS'))
month = qwer('(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)')
year = qwer(rule('FWS'), '(?:', rule('rfc5234.DIGIT'), '){4,}', rule('FWS'))
date = qwer(rule('day'), rule('month'), rule('year'))
hour = qwer('(?:', rule('rfc5234.DIGIT'), '){2}')
minute = qwer('(?:', rule('rfc5234.DIGIT'), '){2}')
second = qwer('(?:', rule('rfc5234.DIGIT'), '){2}')
timeOfDay = qwer(rule('hour'), ':', rule('minute'), '(?::', rule('second'), ')?')
zone = qwer(rule('FWS'), '[+-](?:', rule('rfc5234.DIGIT'), '){4}')
time = qwer(rule('timeOfDay'), rule('zone'))
dateTime = qwer('(?:', rule('dayOfWeek'), ',)?', rule('date'), rule('time'), '(?:', rule('CFWS'), ')?')
