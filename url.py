import socket
import ssl
import urllib.parse


class URL:
    def __init__(self, url):
        if url.startswith("about:"):
            self.scheme = "about"
            self.host = ""
            self.path = url.removeprefix("about:")
            self.port = None
            return

        # file:///절대경로 는 이 컴퓨터의 파일을 가리킨다. 호스트는 비어 있다.
        if url.startswith("file://"):
            self.scheme = "file"
            self.port = None
            rest = url.removeprefix("file://")
            if rest.startswith("/"):
                self.host = ""
                self.path = urllib.parse.unquote(rest)
            else:
                if "/" not in rest:
                    rest += "/"
                self.host, path = rest.split("/", 1)
                self.path = urllib.parse.unquote("/" + path)
            return

        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        self.path = "/" + url
        self.port = None
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)

    def request(self, payload=None):
        if self.scheme == "about":
            return ""
        if self.scheme == "file":
            with open(self.path, encoding="utf8") as f:
                return f.read()

        if self.port is None:
            if self.scheme == "http":
                self.port = 80
            else:
                self.port = 443

        sock = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            sock = ctx.wrap_socket(sock, server_hostname=self.host)
        sock.connect((self.host, self.port))

        method = "POST" if payload else "GET"
        req = "{} {} HTTP/1.0\r\n".format(method, self.path)
        req += "Host: {}\r\n".format(self.host)
        if payload:
            length = len(payload.encode("utf8"))
            req += "Content-Length: {}\r\n".format(length)
        req += "\r\n"
        if payload:
            req += payload
        sock.send(req.encode("utf8"))
        res = sock.makefile("r", encoding="utf8", newline="\r\n")
        statusline = res.readline()
        version, status, explanation = statusline.split(" ", 2)
        res_headers = {}
        while True:
            line = res.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            res_headers[header.casefold()] = value.strip()

        assert "transfer-encoding" not in res_headers
        assert "content-encoding" not in res_headers

        body = res.read()
        sock.close()
        return body

    def __str__(self):
        if self.scheme == "about":
            return "about:" + self.path
        return self.scheme + "://" + self.host + self.port_part() + self.path

    def port_part(self):
        if self.port is None: 
            return ""
        if self.scheme == "https" and self.port == 443:
            return ""
        if self.scheme == "http" and self.port == 80:
            return ""
        return ":" + str(self.port)

    def resolve(self, url):
        if "://" in url:
            return URL(url)
        if not url.startswith("/"):
            dir, _ = self.path.rsplit("/", 1)
            url = dir + "/" + url
        if url.startswith("//"):
            return URL(self.scheme + ":" + url)
        else:
            return URL(self.scheme + "://" + self.host + self.port_part() + url)
