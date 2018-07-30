#!/usr/bin/env python
import sys

try:
    # Python 3
    from http.server import HTTPServer, SimpleHTTPRequestHandler
except ImportError: # Python 2
    from BaseHTTPServer import HTTPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler

class CORSRequestHandler (SimpleHTTPRequestHandler):
    def end_headers (self):
        self.send_header('Access-Control-Allow-Origin', '*')
        SimpleHTTPRequestHandler.end_headers(self)

if __name__ == '__main__':
    server_address = ('localhost', int(sys.argv[1]))
    httpd = HTTPServer(server_address, CORSRequestHandler)
    httpd.serve_forever()


