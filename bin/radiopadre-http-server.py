#!/usr/bin/env python3
import sys, os, re, ssl
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
        print("HTTPServer: requested {}".format(path), file=sys.stderr)
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
    ssl_cert = None
    
    for arg in sys.argv[1:]:
        if re.match("\d+$", arg):
            port = int(arg)
            print(f"HTTPServer: using port {port}", file=sys.stderr)
        elif arg.endswith(".pem"):
            ssl_cert = arg
            print(f"HTTPServer: using SSL certificate {ssl_cert}", file=sys.stderr)
        elif "=" in arg:
            src, dest = arg.split("=", 1)
            src = path_id + src
            path_rewrites.insert(0, (src, dest))
            print("HTTPServer: will rewrite {}->{}".format(src, dest), file=sys.stderr)
    
#    server_address = ("0.0.0.0", port)
#    server_address = ('localhost', port)
    server_address = ('127.0.0.1', port)

    httpd = HTTPServer(server_address, CORSRequestHandler)

    if ssl_cert:
        httpd.socket = ssl.wrap_socket(httpd.socket, certfile=ssl_cert, server_side=True)

    httpd.serve_forever()


