import rfc3986
from qwer import *

# Any CHAR except CTLs or separators
token = qwer('[!#-\'*+\--9A-Z^-z|~]+')

requestUri = qwer('(?:\*|', rule('rfc3986.absoluteUri'), '|', rule('rfc3986.pathAbsolute'), '|', rule('rfc3986.authority'), ')')
