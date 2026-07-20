import socket
import ssl


class URL:
    def __init__(self, url):
        if url.startswith("about:"):
            self.scheme = "about"
            self.host = ""
            self.path = url.removeprefix("about:")
            self.port = None
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

    def request(self):
        if self.scheme == "about":
            return ""

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

        req = "GET {} HTTP/1.0\r\n".format(self.path)
        req += "Host: {}\r\n".format(self.host)
        req += "\r\n"
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
