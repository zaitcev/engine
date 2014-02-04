#
# engine -- the package
#
# Copyright (C) 2014 Pete Zaitcev
# See file COPYING for licensing information (expect GPL 2).
#

import urllib
import urlparse


class AppError(Exception):
    pass
class App400Error(Exception):
    pass
class App404Error(Exception):
    pass
class AppGetError(Exception):
    pass
class AppPostError(Exception):
    pass
class AppGetPostError(Exception):
    pass


# Glie has a py3 compatible definition for safestr, if we want it.
def safestr(u):
    if isinstance(u, unicode):
        return u.encode('utf-8')
    return u

def escapeURLComponent(s):
    # Turn s into a bytes first, quote_plus blows up otherwise
    return unicode(urllib.quote_plus(s.encode("utf-8")))

def escapeURL(s):
    # quote_plus() doesn't work as it clobbers the :// portion of the URL
    # Make sure the resulting string is safe to use within HTML attributes.
    # N.B. Mooneyspace.com hates when we reaplace '&' with %26, so don't.
    # On output, the remaining & will be turned into &quot; by the templating
    # engine. No unescaped-entity problems should result here.
    s = s.replace('"', '%22')
    s = s.replace("'", '%27')
    # s = s.replace('&', '%26')
    s = s.replace('<', '%3C')
    s = s.replace('>', '%3E')
    return s

html_escape_table = {
    ">": "&gt;",
    "<": "&lt;",
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    "\\": "&#92;",
    }

def escapeHTML(text):
    """Escape strings to be safe for use anywhere in HTML

    Should be used for escaping any user-supplied strings values before
    outputting them in HTML. The output is safe to use HTML running text and
    within HTML attributes (e.g. value="%s").

    Escaped chars:
      < and >   HTML tags
      &         HTML entities
      " and '   Allow use within HTML tag attributes
      \\        Shouldn't actually be necessary, but better safe than sorry
    """
    # performance idea: compare with cgi.escape-like implementation
    return "".join(html_escape_table.get(c,c) for c in text)


class Context:
    def __init__(self, pfx, root, method, scheme, netloc, path):
        # prefix: Path where the application is mounted in WSGI or empty string.
        self.prefix = pfx
        # root: The root to Ani-Nouto repo
        self.root = root
        # method: The HTTP method (GET, POST, or garbage)
        self.method = method
        # scheme: http or https
        self._scheme = scheme
        # netloc: host.domain:port
        self._netloc = netloc
        # path: The remaining path after the user. Not the full URL path.
        # This may be empty (we permit user with no trailing slash).
        self.path = path

    def create_jsondict(self):
        userpath = self.prefix+'/'+self.user['name'] ........ no user

        jsondict = {
                    "href_tags": "%s/tags" % userpath,
                    "href_new": "%s/new" % userpath,
                   }

        if self.flogin:
            jsondict["href_export"]= userpath + '/export.xml'
            jsondict["href_login"] = None
            jsondict["hrefa_new"] = \
                    "%s://%s%s/new" % (self._scheme, self._netloc, userpath)
            jsondict["flogin"] = "1"
        else:
            jsondict["href_export"]= None
            jsondict["href_login"] = "%s/login" % userpath
            if self.path and self.path != "login" and self.path != "edit":
                jsondict["href_login"] += '?savedref=%s' % self.path

        userstr = '<a href="%s/">%s</a>' % (userpath, self.user['name']) .....
        jsondict['_main_path'] = userstr

        jsondict['_page_prev'] = "-"
        jsondict['_page_this'] = "-"
        jsondict['_page_next'] = "-"

        return jsondict

    def _parse_args(self, args):
        if args is None:
            return {}

        qdic = urlparse.parse_qs(args)
        for key in qdic:
            qdic[key] = qdic[key][0].decode("utf-8", 'replace')

        return qdic


import main
