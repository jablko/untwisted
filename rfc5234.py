from qwer import *

ALPHA = qwer('[A-Za-z]')

# Use local newlines
CRLF = qwer('\r\n')

DIGIT = qwer('\d')
DQUOTE = qwer('"')
HEXDIG = qwer('[\dABCDEF]')

# 8 bits of data
OCTET = qwer('[\0-\xff]')

# Visible (printing) characters
VCHAR = qwer('[!-~]')

# White space
WSP = qwer('[\t ]')
