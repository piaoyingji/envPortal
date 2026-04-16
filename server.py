import http.server
import socketserver
import urllib.parse
import urllib.request
import urllib.error
import ssl
import sys
import webbrowser
import threading

PORT = 8080

class SimpleTomcatProxy(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path == '/ping.jsp':
            query = urllib.parse.parse_qs(parsed_path.query)
            target_url = query.get('url', [''])[0]
            if not target_url:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(b"ERROR")
                return

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            try:
                req = urllib.request.Request(target_url, method='GET')
                with urllib.request.urlopen(req, timeout=3, context=ctx) as response:
                    code = response.getcode()
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(str(code).encode('utf-8'))
            except urllib.error.HTTPError as e:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(str(e.code).encode('utf-8'))
            except Exception:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(b"ERROR")
            return
        
        super().do_GET()

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        if parsed_path.path == '/auth.jsp':
            try:
                decoded_body = body.decode('utf-8')
                params = urllib.parse.parse_qs(decoded_body)
                pwd = params.get('pwd', [''])[0]
                self.send_response(200)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                if pwd == "nho1234567":
                    self.wfile.write(b"OK")
                else:
                    self.wfile.write(b"NG")
            except Exception:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"NG")
            return

        elif parsed_path.path in ('/update_csv.jsp', '/update_rdp.jsp'):
            filename = 'data.csv' if parsed_path.path == '/update_csv.jsp' else 'rdp.csv'
            try:
                with open(filename, 'wb') as f:
                    f.write(b'\xef\xbb\xbf')
                    f.write(body)
                self.send_response(200)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(b"success")
            except Exception:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(b"Error saving")
            return
        
        self.send_error(404)

def open_browser():
    webbrowser.open(f"http://localhost:{PORT}/index.html")

def run():
    print("=====================================================")
    print(f"组织环境导航系统 (Python 独立服务正在运行)")
    print(f"访问地址: http://localhost:{PORT}/index.html")
    print("模拟了所有的 Tomcat JSP 接口行为，即抛即用")
    print("中止请按 Ctrl+C，关闭此窗口服务将会停止")
    print("=====================================================")
    
    timer = threading.Timer(1.0, open_browser)
    timer.start()

    with socketserver.TCPServer(("", PORT), SimpleTomcatProxy) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止。")
            sys.exit(0)

if __name__ == '__main__':
    run()
