#!/usr/bin/env python3
"""Preview the site locally at the addresses nginx serves on mystima.io.

    python3 tools/serve.py [port]    (default 8000), then open http://localhost:8000

/hiring-teams is served from hiring-teams.html, as nginx's `try_files $uri $uri.html $uri/` does
(deploy/nginx-paths.conf in the app repo), and /terms redirects to /terms/. The forms and plan buttons
still need the Stima app behind the same host.
"""
import functools
import http.server
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        fs = super().translate_path(path)
        if not os.path.exists(fs) and os.path.isfile(fs + ".html"):
            return fs + ".html"
        return fs


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    handler = functools.partial(Handler, directory=str(ROOT))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving {ROOT} on http://localhost:{port}/")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
