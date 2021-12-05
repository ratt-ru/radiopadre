#!/usr/bin/env python3
import sys, os, re, ssl
from http.server import HTTPServer, SimpleHTTPRequestHandler

def info(msg):
    print(msg, file=sys.stderr, flush=True)

info(f"HTTPServer: starting")

path_id = "{}/{}".format(os.getcwd(), os.environ['RADIOPADRE_SESSION_ID'])
# path_rewrites = []
path_rewrites = [(path_id, os.getcwd())]

class CORSRequestHandler (SimpleHTTPRequestHandler):
    def end_headers (self):
        self.send_header('Access-Control-Allow-Origin', '*')
        SimpleHTTPRequestHandler.end_headers(self)

    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        info(f"HTTPServer: requested {path}")
        if not path.startswith(path_id):
            info(f"HTTPServer: ignoring request for {path}")
            return "/dev/null"
        for src, dest in path_rewrites:
            if path.startswith(src):
                newpath = dest + path[len(src):]
                info("HTTPServer: rewriting {path}->{newpath}")
                return newpath
        return path


if __name__ == '__main__':
    info(f"HTTPServer: args {sys.argv}")
    
    ssl_cert = None
#    server_address = ("0.0.0.0", port)
#    server_address = ('localhost', port)
    ip = '127.0.0.1'

    for arg in sys.argv[1:]:
        if re.match("^\d+$", arg):
            port = int(arg)
            info(f"HTTPServer: using port {port}")
        elif re.match("\d+\.\d+.\d+\.\d+", arg):
            ip = arg
            info(f"HTTPServer: using address {ip}")
        elif arg.endswith(".pem"):
            ssl_cert = arg
            info(f"HTTPServer: using SSL certificate {ssl_cert}")
        elif "=" in arg:
            src, dest = arg.split("=", 1)
            src = path_id + src
            path_rewrites.insert(0, (src, dest))
            info(f"HTTPServer: will rewrite {src}->{dest}")
    
    httpd = HTTPServer((ip, port), CORSRequestHandler)

    if ssl_cert:
        httpd.socket = ssl.wrap_socket(httpd.socket, certfile=ssl_cert, server_side=True)

    info("HTTPServer: serving")
    httpd.serve_forever()


