import socket
import ssl
import tkinter

from constants import HEIGHT, HSTEP, SCROLL_STEP, VSTEP, WIDTH

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.canvas.pack()
        self.scroll = 0
        self.window.bind("<Down>", self.scroll_down)

    def scroll_down(self, event):
        self.scroll += SCROLL_STEP
        self.draw()
    
    def load(self, url):
        body = url.request()
        text = lex(body)
        self.display_list = layout(text)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c)

class URL:
    def __init__(self, url):
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
        version, status, explanation = statusline.split(" ",2)
        res_headers = {}
        while True:
            line = res.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            res_headers[header.casefold()] = value.strip()

        assert "transfer-encoding" not in res_headers
        assert "content-encoding" not in res_headers

        body = res.read()
        sock.close()
        return lex(body)

def lex(body):
    text = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            text += c
    return text

def layout(text):
    cursor_x, cursor_y = HSTEP, VSTEP
    display_list = []
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x > WIDTH - HSTEP:
            cursor_x = HSTEP
            cursor_y += VSTEP
    return display_list

if __name__ == "__main__":
    import sys
    browser = Browser()
    browser.window.after(10, lambda: browser.load(URL(sys.argv[1])))
    browser.window.mainloop()
