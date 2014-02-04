#
# The WSGI wrapper for Ani-Nouto Engine
#
# Copyright (C) 2014 Pete Zaitcev
# See file COPYING for licensing information (expect GPL 2).
#

import json
import types
# import sys

# Instead of ROOT we use  SetEnv engine.root /var/lib/ani-nouto
# ROOT = "/var/lib/ani-nouto"

# Replaced by  WSGIDaemonProcess engine python-path=/usr/lib/engine-mod
# sys.path = sys.path + [ '/usr/lib/engine-mod' ]

import engine

# Return an index (paginated) as selected by the path.
def do_index(environ, start_response, path):

    # The prefix must be either empty or absolute (no relative or None).
    pfx = environ['SCRIPT_NAME']
    if pfx == None or pfx == "/":
        pfx = ""
    if pfx != "" and pfx[0] != "/":
        pfx = "/"+pfx

    scheme = environ['wsgi.url_scheme']
    netloc = environ['HTTP_HOST']

    # Query is already split away by the CGI.
    parsed = path.split("/", 2)

    if len(parsed) >= 3:
        path = parsed[2]
    else:
        path = ""

    root = environ['engine.root']

    ctx = engine.Context(pfx, root, method, scheme, netloc, path)
    return engine.main.app(start_response, ctx)

def application(environ, start_response):

    path = environ['PATH_INFO']
    if isinstance(path, basestring):
        if not isinstance(path, unicode):
            try:
                path = unicode(path, 'utf-8')
            except UnicodeDecodeError:
                start_response("400 Bad Request",
                               [('Content-type', 'text/plain')])
                return ["400 Unable to decode UTF-8 in path\r\n"]

    try:
        if path == None or path == "" or path == "/":
            path = "/ticker"
        return do_index(environ, start_response, path)

    except engine.AppError, e:
        start_response("500 Internal Error", [('Content-type', 'text/plain')])
        return [engine.safestr(unicode(e)), "\r\n"]
    except engine.App400Error, e:
        start_response("400 Bad Request", [('Content-type', 'text/plain')])
        return ["400 Bad Request: %s\r\n" % engine.safestr(unicode(e))]
    except engine.AppLoginError, e:
        start_response("403 Not Permitted", [('Content-type', 'text/plain')])
        return ["403 Not Logged In\r\n"]
    except engine.App404Error, e:
        start_response("404 Not Found", [('Content-type', 'text/plain')])
        return [engine.safestr(unicode(e)), "\r\n"]
    except engine.AppGetError, e:
        start_response("405 Method Not Allowed",
                       [('Content-type', 'text/plain'), ('Allow', 'GET')])
        return ["405 Method %s not allowed\r\n" % engine.safestr(unicode(e))]
    except engine.AppPostError, e:
        start_response("405 Method Not Allowed",
                       [('Content-type', 'text/plain'), ('Allow', 'POST')])
        return ["405 Method %s not allowed\r\n" % engine.safestr(unicode(e))]
    except engine.AppGetPostError, e:
        start_response("405 Method Not Allowed",
                       [('Content-type', 'text/plain'), ('Allow', 'GET, POST')])
        return ["405 Method %s not allowed\r\n" % engine.safestr(unicode(e))]

# We do not have __main__ in WSGI.
# if __name__.startswith('_mod_wsgi_'):
#    ...
