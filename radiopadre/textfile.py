import os
import traceback
import cgi
import subprocess

import IPython.display
from IPython.display import HTML, display

import radiopadre
import radiopadre.file
from radiopadre.render import render_title, render_url, render_preamble


class TextFile(radiopadre.file.FileBase):

    def _repr_html_(self):
        return self.html(tail=10)

    def __str__(self):
        return "%s modified %s:\n%s" % (self.path, self.update_mtime(), self.tail(-10))

    def html(self,tail=None,head=None,fs=.8):
        txt = render_preamble()
        txt += "<A HREF=%s target='_blank'>" % render_url(self.fullpath) + \
                render_title(self.path) + "</A> modified %s:" % self.update_mtime();
        txt += """\n<PRE style="font-size: %d%%; line-height: 110%%">"""%(fs*100) + \
                (cgi.escape(self.head(head)) if head else "") + \
                ("...\n" if head and tail else "") + \
                (cgi.escape(self.tail(tail)) if tail else "") + \
                "</PRE>"
        return txt

    def head(self,num=10):
        try:
            return subprocess.check_output(["head","-"+str(num),self.fullpath])
        except Exception,exc:
            return str(exc)

    def tail(self,num=10):
        try:
            return subprocess.check_output(["tail","-"+str(abs(num)),self.fullpath])
        except Exception,exc:
            return str(exc)

    def show(self,tail=10,head=None,fs=.8,refresh=None,**kw):
        IPython.display.display(HTML(self.html(head=head,tail=tail,fs=fs)))
