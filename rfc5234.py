from qwer import *

ALPHA = qwer('[A-Za-z]')

# Use local newlines
CRLF = qwer('\r\n')

DIGIT = qwer('\d')
DQUOTE = qwer('"')
HEXDIG = qwer('[0-9ABCDEF]')

# Visible (printing) characters
VCHAR = qwer('[!-~]')

# White space
WSP = qwer('[\t ]')
