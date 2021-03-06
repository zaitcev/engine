#
# Engine -- Main Application
#
# Copyright (C) 2014 Pete Zaitcev
#           (C) 2012 Christian Aichinger
# See file COPYING for licensing information (expect GPL 2).
#

import time
import urlparse
import base64
import os
import hashlib

from engine import (App400Error, App404Error, AppGetError, AppGetPostError)
import engine
import tagbase ........
from template import Template, TemplateElemLoop, TemplateElemCond

PAGESZ = 25

BLACKSTAR = u"\u2605"     # "&#9733;"
WHITESTAR = u"\u2606"     # "&#9734;"

def page_back(mark):
    mark = mark.pred()
    if mark == None:
        return None
    # In all other cases, we'll return something, even if 1 entry back.
    n = 1
    while n < PAGESZ:
        m = mark.pred()
        if m == None:
            return mark
        mark = m
        n += 1
    return mark

def page_anchor_html(mark, path, text):
    if mark == None:
        return '-'
    (stamp0, stamp1) = mark.key()
    return '<a href="%s/page.%d.%02d">%s</a>' % (path, stamp0, stamp1, text)

def mark_anchor_html(mark, path, text):
    if mark == None:
        return '-'
    (stamp0, stamp1) = mark.key()
    return '<a href="%s/mark.%d.%02d">%s</a>' % (path, stamp0, stamp1, text)

def find_post_args(ctx):
    rdic = {}
    for key in ['title', 'href', 'tags', 'extra']:
        rdic[key] = ctx.get_pinput_arg(key) or ""

    if not rdic["href"] or not rdic["tags"]:
        raise App400Error("The URL and tags are mandatory")

    return rdic

def findmark(mark_str):
    if not mark_str:
        raise App400Error("no mark tag")
    p = mark_str.split(".")
    try:
        stamp0 = int(p[0])
        stamp1 = int(p[1])
    except (ValueError, IndexError):
        raise App400Error("bad mark format")
    return (stamp0, stamp1)

def page_any_html(start_response, ctx, mark_top):
    userpath = ctx.prefix+'/'+ctx.user['name']

    jsondict = ctx.create_jsondict()

    what = mark_top.tag()
    if what:
        path = userpath + '/' + slasti.escapeURL(what)
        jsondict['_main_path'] += ' / '+slasti.escapeHTML(what)+'/'
    else:
        path = userpath
        jsondict['_main_path'] += ' / '+BLACKSTAR

    jsondict["marks"] = []

    mark = mark_top
    mark_next = None
    n = 0
    for n in range(PAGESZ):
        jsondict["marks"].append(mark.to_jsondict(userpath))

        mark_next = mark.succ()
        if mark_next == None:
            break
        mark = mark_next

    jsondict.update({
         "_page_prev": page_anchor_html(page_back(mark_top), path, "&laquo;"),
         "_page_this": page_anchor_html(mark_top,            path, BLACKSTAR),
         "_page_next": page_anchor_html(mark_next,           path, "&raquo;")
            })

    start_response("200 OK", [('Content-type', 'text/html; charset=utf-8')])
    return [template_html_page.substitute(jsondict)]

def page_mark_html(start_response, ctx, stamp0, stamp1):
    mark = ctx.base.lookup(stamp0, stamp1)
    if mark == None:
        # We have to have at least one mark to display a page
        raise App404Error("Page not found: "+str(stamp0)+"."+str(stamp1))
    if ctx.method != 'GET':
        raise AppGetError(ctx.method)
    return page_any_html(start_response, ctx, mark)

def page_tag_html(start_response, ctx, tag, stamp0, stamp1):
    mark = ctx.base.taglookup(tag, stamp0, stamp1)
    if mark == None:
        raise App404Error("Tag page not found: "+tag+" / "+
                           str(stamp0)+"."+str(stamp1))
    if ctx.method != 'GET':
        raise AppGetError(ctx.method)
    return page_any_html(start_response, ctx, mark)

def page_empty_html(start_response, ctx):
    username = ctx.user['name']
    userpath = ctx.prefix+'/'+username

    start_response("200 OK", [('Content-type', 'text/html; charset=utf-8')])
    jsondict = ctx.create_jsondict()
    jsondict['_main_path'] += ' / [-]'
    jsondict.update({
                "marks": [],
               })
    return [template_html_page.substitute(jsondict)]

def delete_post(start_response, ctx):
    path = ctx.prefix+'/'+ctx.user['name']

    (stamp0, stamp1) = findmark(ctx.get_pinput_arg("mark"))
    ctx.base.delete(stamp0, stamp1);

    start_response("200 OK", [('Content-type', 'text/html; charset=utf-8')])
    jsondict = ctx.create_jsondict()
    return [template_html_delete.substitute(jsondict)]

def mark_post(start_response, ctx, mark):
    argd = find_post_args(ctx)

    tags = tagbase.split_marks(argd['tags'])
    (stamp0, stamp1) = mark.key()
    ctx.base.edit1(stamp0, stamp1,
                   argd['title'], argd['href'], argd['extra'], tags)

    # Since the URL stays the same, we eschew 303 here.
    # Just re-read the base entry with a lookup and pretend this was a GET.
    mark = ctx.base.lookup(stamp0, stamp1)
    if mark == None:
        raise App404Error("Mark not found: "+str(stamp0)+"."+str(stamp1))
    return mark_get(start_response, ctx, mark, stamp0)

def mark_get(start_response, ctx, mark, stamp0):
    path = ctx.prefix+'/'+ctx.user['name']

    start_response("200 OK", [('Content-type', 'text/html; charset=utf-8')])
    jsondict = ctx.create_jsondict()
    jsondict.update({
                "mark": mark.to_jsondict(path),
                "href_edit": mark.get_editpath(path),
                "_page_prev": mark_anchor_html(mark.pred(), path, "&laquo;"),
                "_page_this": mark_anchor_html(mark,        path, WHITESTAR),
                "_page_next": mark_anchor_html(mark.succ(), path, "&raquo;")
               })
    return [template_html_mark.substitute(jsondict)]

def one_mark_html(start_response, ctx, stamp0, stamp1):
    mark = ctx.base.lookup(stamp0, stamp1)
    if mark == None:
        raise App404Error("Mark not found: "+str(stamp0)+"."+str(stamp1))
    if ctx.method == 'GET':
        return mark_get(start_response, ctx, mark, stamp0)
    if ctx.method == 'POST':
        #if ctx.flogin == 0:
        #    raise AppLoginError()
        return mark_post(start_response, ctx, mark)
    raise AppGetPostError(ctx.method)

def root_mark_html(start_response, ctx):
    if ctx.method != 'GET':
        raise AppGetError(ctx.method)
    mark = ctx.base.first()
    if mark == None:
        return page_empty_html(start_response, ctx)
    return page_any_html(start_response, ctx, mark)
    ## The non-paginated version
    #
    # response_headers = [('Content-type', 'text/html')]
    # start_response("200 OK", response_headers)
    # output = ["<html><body>\n"]
    #
    # left_lead = '  <h2 style="margin-bottom:0">'+\
    #             '<a href="%s/">%s</a></h2>\n' % \
    #             (ctx.path, ctx.user['name']))
    # spit_lead(output, ctx, left_lead)
    #
    # for mark in base:
    #     (stamp0, stamp1) = mark.key()
    #     datestr = time.strftime("%Y-%m-%d", time.gmtime(stamp0))
    #
    #     output.append("<p>%s %s " % \
    #                   (datestr, mark_anchor_html(mark, ctx.path, WHITESTAR)))
    #     output.append(mark.html())
    #     output.append("</p>\n")
    #
    # output.append("</body></html>\n")
    # return output

def root_tag_html(start_response, ctx, tag):
    mark = ctx.base.tagfirst(tag)
    if mark == None:
        # Not sure if this may happen legitimately, so 404 for now.
        raise App404Error("Tag page not found: "+tag)
    if ctx.method != 'GET':
        raise AppGetError(ctx.method)
    return page_any_html(start_response, ctx, mark)

class MarkDumper(object):
    def __init__(self, base, user):
        self.username = user['name']
        self.base = tagbase.TagBase(base.dirname)
    # <posts user="zaitcev" update="2010-12-16T20:17:55Z" tag="" total="860">
    # We omit total. Also, we noticed that Del.icio.us often miscalculates
    # the total, so obviously it's not used by any applications.
    # We omit the last update as well. Our data base does not keep it.
    def __iter__(self):
        self.base.open()
        try:
            yield '<?xml version="1.0" encoding="UTF-8"?>\n'
            yield '<posts user="'+slasti.safestr(self.username)+'" tag="">\n'
            for mark in self.base:
                yield slasti.safestr(mark.xml())
            yield '</posts>\n'
        finally:
            self.base.close()

# full_mark_html() would be a Netscape bookmarks file, perhaps.
def full_mark_xml(start_response, ctx):
    if ctx.method != 'GET':
        raise AppGetError(ctx.method)
    response_headers = [('Content-type', 'text/xml; charset=utf-8')]
    start_response("200 OK", response_headers)
    return MarkDumper(ctx.base, ctx.user)

def full_tag_html(start_response, ctx):
    if ctx.method != 'GET':
        raise AppGetError(ctx.method)

    userpath = ctx.prefix + '/' + ctx.user['name']
    start_response("200 OK", [('Content-type', 'text/html; charset=utf-8')])
    jsondict = ctx.create_jsondict()
    jsondict['_main_path'] += ' / tags'
    jsondict["tags"] = []
    for tag in ctx.base.tagcurs():
        ref = tag.key()
        jsondict["tags"].append(
            {"href_tag": '%s/%s/' % (userpath, slasti.escapeURLComponent(ref)),
             "name_tag": ref,
             "num_tagged": tag.num(),
            })
    return [template_html_tags.substitute(jsondict)]

def new_form(start_response, ctx):
    userpath = ctx.prefix + '/' + ctx.user['name']
    title = ctx.get_query_arg('title')
    href = ctx.get_query_arg('href')

    jsondict = ctx.create_jsondict()
    jsondict['_main_path'] += ' / ['+WHITESTAR+']'
    jsondict.update({
            "id_title": "title1",
            "id_button": "button1",
            "href_editjs": ctx.prefix + '/edit.js',
            "mark": None,
            "action_edit": userpath + '/edit',
            "val_title": title,
            "val_href": href,
        })
    start_response("200 OK", [('Content-type', 'text/html; charset=utf-8')])
    return [template_html_editform.substitute(jsondict)]

def edit_form(start_response, ctx):
    userpath = ctx.prefix + '/' + ctx.user['name']

    (stamp0, stamp1) = findmark(ctx.get_query_arg("mark"))
    mark = ctx.base.lookup(stamp0, stamp1)
    if not mark:
        raise App400Error("not found: "+str(stamp0)+"."+str(stamp1))

    jsondict = ctx.create_jsondict()
    jsondict['_main_path'] += ' / '+mark_anchor_html(mark, userpath, WHITESTAR)
    jsondict.update({
        "id_title": "title1",
        "id_button": "button1",
        "href_editjs": ctx.prefix + '/edit.js',
        "mark": mark.to_jsondict(userpath),
        "action_edit": "%s/mark.%d.%02d" % (userpath, stamp0, stamp1),
        "action_delete": userpath + '/delete',
        "val_title": mark.title,
        "val_href": mark.url,
        "val_tags": ' '.join(mark.tags),
        "val_note": mark.note,
        })

    start_response("200 OK", [('Content-type', 'text/html; charset=utf-8')])
    return [template_html_editform.substitute(jsondict)]

# The name edit_post() is a bit misleading, because POST to /edit is used
# to create new marks, not to edit existing ones (see mark_post() for that).
def edit_post(start_response, ctx):
    username = ctx.user['name']
    userpath = ctx.prefix+'/'+username

    argd = find_post_args(ctx)
    tags = tagbase.split_marks(argd['tags'])

    stamp0 = int(time.time())
    stamp1 = ctx.base.add1(stamp0,
                           argd['title'], argd['href'], argd['extra'], tags)
    if stamp1 < 0:
        raise App404Error("Out of fix: %d" % stamp0)

    redihref = '%s/mark.%d.%02d' % (userpath, stamp0, stamp1)

    response_headers = [('Content-type', 'text/html; charset=utf-8')]
    response_headers.append(('Location', slasti.safestr(redihref)))
    start_response("303 See Other", response_headers)

    jsondict = { "href_redir": redihref }
    return [template_html_redirect.substitute(jsondict)]

def new(start_response, ctx):
    if ctx.method == 'GET':
        return new_form(start_response, ctx)
    raise AppGetError(ctx.method)

def edit(start_response, ctx):
    if ctx.method == 'GET':
        return edit_form(start_response, ctx)
    if ctx.method == 'POST':
        return edit_post(start_response, ctx)
    raise AppGetPostError(ctx.method)

def delete(start_response, ctx):
    if ctx.method == 'POST':
        return delete_post(start_response, ctx)
    raise AppPostError(ctx.method)

#
# Path is either index, a direct path, or a special page.
#
# Index can have page number like "index/3/".
# By convention, all posts are included into the index named "ticker".
#
# Example of index paths:
#  "ticker"
#  "category/seiyuu"
#  "category/anime/nodame"
#  "2014/01"
#
# Direct path is "{date}/{slug}/" like this:
#  2014/01/25/girls-und-panzer-suspended/
#
# Special pages:
#  "category" -- list of categories
#  "archive" -- list of year/month
#
def app(start_response, ctx):
    pathv = ctx.path.split('/', 5)

    # First, we check for known indexes
    index_name = pathv[0]
    if index_name.find('..') != -1:
        raise App400Error("Bad tag name")
    try:
        ifp = open(os.path.join(ctx.root, index_name))
    except OSError:
        ifp = None
    if ifp:
        index = read_index(ifp)
        ifp.close()
        .... page_number
        return index_page_html(start_response, ctx, index, page_number)

    # Okay, maybe a direct path
    ..................

    raise App404Error("Not found")

...........
    if ctx.path == "new":
        return new(start_response, ctx)
    if ctx.path == "edit":
        return edit(start_response, ctx)
    if ctx.path == "delete":
        return delete(start_response, ctx)
    if ctx.path == "":
        return root_mark_html(start_response, ctx)
    if ctx.path == "export.xml":
        return full_mark_xml(start_response, ctx)
.............
    if ctx.path == "tags":
        return full_tag_html(start_response, ctx)
    if "/" in ctx.path:
        # Trick: by splitting with limit 2 we prevent users from poisoning
        # the tag with slashes. Not that it matters all that much, but still.
        p = ctx.path.split("/", 2)
        tag = p[0]
        page = p[1]
        if page == "":
            return root_tag_html(start_response, ctx, tag)
        p = page.split(".")
        if len(p) != 3:
            raise App404Error("Not found: "+ctx.path)
        try:
            stamp0 = int(p[1])
            stamp1 = int(p[2])
        except ValueError:
            raise App404Error("Not found: "+ctx.path)
        if p[0] == "page":
            return page_tag_html(start_response, ctx, tag, stamp0, stamp1)
        raise App404Error("Not found: "+ctx.path)
    else:
        p = ctx.path.split(".")
        if len(p) != 3:
            raise App404Error("Not found: "+ctx.path)
        try:
            stamp0 = int(p[1])
            stamp1 = int(p[2])
        except ValueError:
            raise App404Error("Not found: "+ctx.path)
        if p[0] == "mark":
            return one_mark_html(start_response, ctx, stamp0, stamp1)
        if p[0] == "page":
            return page_mark_html(start_response, ctx, stamp0, stamp1)
        raise App404Error("Not found: "+ctx.path)

template_html_header = Template("""
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
</head>
<body>
""")

# The &href should be escaped (although Firefox eats it fine)
template_html_controls = Template(
"""
        [<a href="$href_new">new</a>]
        [<a href="javascript:
 var F=document;
 ref = '';
 ref += '$hrefa_new';
 ref += '?title=' + F.title;
 ref += '&href=' + location.href;
 F.location = ref" title="Drag This To Toolbar">bm</a>]
        [<a href="$href_export">e</a>]
""")

template_html_body_top = Template("""
<table width="100%" style="background: #ebf7eb"
 border=0 cellpadding=1 cellspacing=0>
<tr valign="top">
    <td align="left">
        <h2 style="margin-bottom:0"> $_main_path </h2>
    </td>
    <td align="right">
""",
    TemplateElemCond('flogin',
        template_html_controls,
"""
        [<a href="$href_login">login</a>]
"""
    ),
"""
        [<b><a href="$href_tags">tags</a></b>]
    </td>
</tr></table>
""")

# XXX The price of no-#if is &laquo; and &raquo; hardwired in dict. Parameter?
template_html_body_bottom = Template("""
<hr />
[$_page_prev][$_page_this][$_page_next]<br />
</body></html>
""")

template_html_tag = Template(
'      <a href="${tag.href_tag}">${tag.name_tag}</a>\r\n'
)

template_html_pagemark = Template("""
<p>${mark.date} [<a href="${mark.href_mark}">&#9734;</a>]
   <a href="${mark.href_mark_url}">${mark.title}</a>
""",
    TemplateElemCond('mark.note', '<br />${mark.note}', None),
"""
   <br />
""",
    TemplateElemLoop('tag','mark.tags',template_html_tag),
"""
</p>
"""
)

template_html_page = Template(
    template_html_header,
    template_html_body_top,
    TemplateElemLoop('mark','marks',template_html_pagemark),
    template_html_body_bottom)

template_html_mark = Template(
    template_html_header,
    template_html_body_top,
"""
    <p>${mark.date}<br />
          <a href="${mark.href_mark_url}">${mark.title}</a> <br />
""",
          TemplateElemCond('mark.note', '      ${mark.note}<br />\r\n', None),
          TemplateElemLoop('tag','mark.tags',template_html_tag),
"""
    </p>
""",
    TemplateElemCond('flogin',
        '    <p>[<a href="$href_edit">edit</a>]</p>\r\n', None),
    template_html_body_bottom)

template_html_tags = Template(
    template_html_header,
    template_html_body_top,
"""
<p>
""",
    TemplateElemLoop('tag','tags',
        '  <a href="${tag.href_tag}">${tag.name_tag}</a>'+
        ' ${tag.num_tagged}<br />\r\n'),
"""
</p>
<hr />
</body></html>
""")

template_html_delete = Template(
    template_html_header,
    template_html_body_top,
"""
    <p>Deleted.</p>
    </body></html>
""")

template_html_login = Template(
    template_html_header,
"""
    <form action="$action_login" method="POST">
      $username:
      <input name=password type=password size=32 maxlength=32 />
      <input name=OK type=submit value="Enter" />
""",
    TemplateElemCond('savedref',
      '    <input name=savedref type=hidden value="$savedref" />', None),
"""
    </form>
    </body>
    </html>
""")

template_html_redirect = Template(
    template_html_header,
"""
    <p><a href="$href_redir">See Other</a></p>
    </body></html>
""")

template_html_editform = Template(
    template_html_header,
    template_html_body_top,
    """
    <script src="$href_editjs"></script>
    <form action="$action_edit" method="POST" name="editform">
     <table>
     <tr>
      <td>Title
      <td>
        <input name="title" type="text" size=80 maxlength=1023 id="$id_title"
               value="${val_title:-}" />
""",
        TemplateElemCond('mark', None,
"""
        <input name="preload" value="Preload" type="button" id="$id_button"
         onclick="preload_title('$href_fetch', '$id_title', '$id_button');" />
"""
        ),
"""
     </tr><tr>
      <td>URL
      <td><input name="href" type="text" size=95 maxlength=1023
           value="${val_href:-}"/>
     </tr><tr>
      <td>tags
      <td><input name="tags" type="text" size=95 maxlength=1023
           value="${val_tags:-}"/>
     </tr><tr>
      <td>Extra
      <td><input name="extra" type="text" size=95 maxlength=1023
           value="${val_note:-}"/>
     </tr><tr>
      <td colspan=2><input name=action type=submit value="Save" />
     </tr></table>
    </form>

""",
    TemplateElemCond('action_delete',
    """
    <p>or</p>
    <form action="$action_delete" method="POST">
      <input name=mark type=hidden value="${mark.key}" />
      <input name=action type=submit value="Delete" />
      (There is no undo.)
    </form>
    """, None),
"""
    <hr />
    </body></html>
""")

template_simple_output = Template("""$output""")
