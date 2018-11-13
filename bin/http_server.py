#!/usr/bin/env python
import sys
import os

try:
    # Python 3
    from http.server import HTTPServer, SimpleHTTPRequestHandler
except ImportError: # Python 2
    from BaseHTTPServer import HTTPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler

path_rewrites = []

class CORSRequestHandler (SimpleHTTPRequestHandler):
    def end_headers (self):
        self.send_header('Access-Control-Allow-Origin', '*')
        SimpleHTTPRequestHandler.end_headers(self)

    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        for src, dest in path_rewrites:
            if path.startswith(src):
                newpath = dest + path[len(src):]
                print("Rewriting {}->{}".format(path, newpath))
                return newpath
        return path

if __name__ == '__main__':
    for arg in sys.argv[2:]:
        if "=" in arg:
            src, dest = arg.split("=", 1)
            src = os.getcwd() + src
            path_rewrites.append((src, dest))
            print("Will rewrite {}->{}".format(src, dest))

    server_address = ('localhost', int(sys.argv[1]))
    httpd = HTTPServer(server_address, CORSRequestHandler)
    httpd.serve_forever()


