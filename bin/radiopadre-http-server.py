#!/usr/bin/env python3
import sys
import os

from http.server import HTTPServer, SimpleHTTPRequestHandler

path_id = "{}/{}".format(os.getcwd(), os.environ['RADIOPADRE_SESSION_ID'])
# path_rewrites = []
path_rewrites = [(path_id, os.getcwd())]

class CORSRequestHandler (SimpleHTTPRequestHandler):
    def end_headers (self):
        self.send_header('Access-Control-Allow-Origin', '*')
        SimpleHTTPRequestHandler.end_headers(self)

    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        print("HTTPServer: requested {}".format(path))
        if not path.startswith(path_id):
            print("HTTPServer: ignoring request for {}".format(path))
            return "/dev/null"
        for src, dest in path_rewrites:
            if path.startswith(src):
                newpath = dest + path[len(src):]
                print("HTTPServer: rewriting {}->{}".format(path, newpath))
                return newpath
        return path

if __name__ == '__main__':
    for arg in sys.argv[2:]:
        if "=" in arg:
            src, dest = arg.split("=", 1)
            src = path_id + src
            path_rewrites.insert(0, (src, dest))
            print("HTTPServer: will rewrite {}->{}".format(src, dest))
    port = int(sys.argv[1])
    print("HTTPServer: starting on port {}".format(port))

    server_address = ("0.0.0.0", port)
#    server_address = ('localhost', port)
    httpd = HTTPServer(server_address, CORSRequestHandler)
    httpd.serve_forever()


