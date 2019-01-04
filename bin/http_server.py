#!/usr/bin/env python
from __future__ import print_function
import sys
import os

try:
    # Python 3
    from http.server import HTTPServer, SimpleHTTPRequestHandler
except ImportError: # Python 2
    from BaseHTTPServer import HTTPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler

path_id = "{}/{}".format(os.getcwd(), os.environ['RADIOPADRE_SESSION_ID'])
# path_rewrites = []
path_rewrites = [(path_id, os.getcwd())]

class CORSRequestHandler (SimpleHTTPRequestHandler):
    def end_headers (self):
        self.send_header('Access-Control-Allow-Origin', '*')
        SimpleHTTPRequestHandler.end_headers(self)

    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        if not path.startswith(path_id):
            print("HTTPServer: ignoring request for {}".format(path), file=sys.stderr)
            return "/dev/null"
        for src, dest in path_rewrites:
            if path.startswith(src):
                newpath = dest + path[len(src):]
                print("HTTPServer: rewriting {}->{}".format(path, newpath), file=sys.stderr)
                return newpath
        return path

if __name__ == '__main__':
    for arg in sys.argv[2:]:
        if "=" in arg:
            src, dest = arg.split("=", 1)
            src = os.getcwd() + src
            path_rewrites.append((src, dest))
            print("HTTPServer: will rewrite {}->{}".format(src, dest))
    port = int(sys.argv[1])
    print("HTTPServer: starting on port {}".format(port))

    server_address = ('localhost', port)
    httpd = HTTPServer(server_address, CORSRequestHandler)
    httpd.serve_forever()


