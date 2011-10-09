import rfc5234
from qwer import *

decOctet = qwer('(?:', rule('rfc5234.DIGIT'), # 0-9
  '|[1-9]', rule('rfc5234.DIGIT'), # 10-99
  '|1(?:', rule('rfc5234.DIGIT'), '){2}', # 100-199
  '|2[0-4]', rule('rfc5234.DIGIT'), # 200-249
  '|25[0-5])') # 250-255

ipv4Address = qwer(rule('decOctet'), '\.', rule('decOctet'), '\.', rule('decOctet'), '\.', rule('decOctet'))

# 16 bits of address represented in hexadecimal
h16 = qwer('(?:', rule('rfc5234.HEXDIG'), '){1,4}')

# least-significant 32 bits of address
ls32 = qwer('(?:', rule('h16'), ':', rule('h16'), '|', rule('ipv4Address'), ')')

ipv6Address = qwer('(?:(?:', rule('h16'), ':){6}', rule('ls32'),
  '|::(?:', rule('h16'), ':){5}', rule('ls32'),
  '|(?:', rule('h16'), ')?::(?:', rule('h16'), ':){4}', rule('ls32'),
  '|(?:(?:', rule('h16'), ':){,1}', rule('h16'), ')?::(?:', rule('h16'), ':){3}', rule('ls32'),
  '|(?:(?:', rule('h16'), ':){,2}', rule('h16'), ')?::(?:', rule('h16'), ':){2}', rule('ls32'),
  '|(?:(?:', rule('h16'), ':){,3}', rule('h16'), ')?::', rule('h16'), ':', rule('ls32'),
  '|(?:(?:', rule('h16'), ':){,4}', rule('h16'), ')?::', rule('ls32'),
  '|(?:(?:', rule('h16'), ':){,5}', rule('h16'), ')?::', rule('h16'),
  '|(?:(?:', rule('h16'), ':){,6}', rule('h16'), ')?::)')
unreserved = qwer('(?:', rule('rfc5234.ALPHA'), '|', rule('rfc5234.DIGIT'), '|[-._~])')
subDelims = qwer('[!$&\'()*+,;=]')
ipvFuture = qwer('v(?:', rule('rfc5234.HEXDIG'), ')+\.(?:', rule('unreserved'), '|', rule('subDelims'), '|:)+')
ipLiteral = qwer('\[(?:', rule('ipv6Address'), '|', rule('ipvFuture'), ')]')
scheme = qwer(rule('rfc5234.ALPHA'), '(?:', rule('rfc5234.ALPHA'), '|', rule('rfc5234.DIGIT'), '|[+\-.])*')
pctEncoded = qwer('%', rule('rfc5234.HEXDIG'), rule('rfc5234.HEXDIG'))
userinfo = qwer('(?:', rule('unreserved'), '|', rule('pctEncoded'), '|', rule('subDelims'), '|:)*')
regName = qwer('(?:', rule('unreserved'), '|', rule('pctEncoded'), '|', rule('subDelims'), ')*')
host = qwer('(?:', rule('ipLiteral'), '|', rule('ipv4Address'), '|', rule('regName'), ')')
port = qwer('(?:', rule('rfc5234.DIGIT'), ')*')
authority = qwer('(?:', rule('userinfo'), '@)?', rule('host'), '(?::', rule('port'), ')?')
pchar = qwer('(?:', rule('unreserved'), '|', rule('pctEncoded'), '|', rule('subDelims'), '|:@)')
segment = qwer('(?:', rule('pchar'), ')*')
pathAbempty = qwer('(?:/', rule('segment'), ')*')
segmentNz = qwer('(?:', rule('pchar'), ')+')
pathAbsolute = qwer('/(?:', rule('segmentNz'), '(?:/', rule('segment'), ')*)?')
pathRootless = qwer(rule('segmentNz'), '(?:/', rule('segment'), ')*')
pathEmpty = qwer()
hierPart = qwer('(?://', rule('authority'), rule('pathAbempty'), '|', rule('pathAbsolute'), '|', rule('pathRootless'), '|', rule('pathEmpty'), ')')
query = qwer('(?:', rule('pchar'), '|/|\?)*')
absoluteUri = qwer(rule('scheme'), ':', rule('hierPart'), '(?:\?', rule('query'), ')?')

fragment = qwer('(?:', rule('pchar'), '|/|\?)*')
uri = qwer(rule('scheme'), ':', rule('hierPart'), '(?:\?', rule('query'), ')?(?:#', rule('fragment'), ')?')
segmentNzNc = qwer('(?:', rule('unreserved'), '|', rule('pctEncoded'), '|', rule('subDelims'), '|@)+')
pathNoscheme = qwer(rule('segmentNzNc'), '(?:/', rule('segment'), ')*')
relativePart = qwer('(?://', rule('authority'), rule('pathAbempty'), '|', rule('pathAbsolute'), '|', rule('pathNoscheme'), '|', rule('pathEmpty'), ')')
relativeRef = qwer(rule('relativePart'), '(?:\?', rule('query'), ')?(?:#', rule('fragment'), ')?')
uriReference = qwer('(?:', rule('uri'), '|', rule('relativeRef'), ')')
