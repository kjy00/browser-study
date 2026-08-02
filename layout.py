import tkinter
import tkinter.font

from constants import HSTEP, VSTEP

FONTS = {}


def get_font(size: int, weight: str, style: str):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]


class Text:
    def __init__(self, text: str):
        self.text = text


class Tag:
    def __init__(self, tag: str):
        self.tag = tag


class Layout:
    def __init__(self, tokens, width: int):
        self.display_list = []
        self.line = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 16
        self.abbr = False
        self.width = width
        for tok in tokens:
            self.token(tok)
        self.flush()

    def token(self, tok):
        if isinstance(tok, Text):
            self.word(tok)
        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4
        elif tok.tag == "abbr":
            self.abbr = True
        elif tok.tag == "/abbr":
            self.abbr = False
        elif tok.tag == "br":
            self.flush()
        elif tok.tag == "/p":
            self.flush()
            self.cursor_y += VSTEP

    def word(self, tok):
        font = get_font(self.size, self.weight, self.style)
        for word in tok.text.split():
            if self.abbr:
                for c in word:
                    if c.islower():
                        self.add_line(c.upper(), get_font(self.size - 2, "bold", self.style))
                    else:
                        self.add_line(c, font)
            else:
                self.add_line(word, font)
            self.cursor_x += font.measure(" ")

    def add_line(self, text, font):
        w = font.measure(text)
        if self.cursor_x + w > self.width - HSTEP:
            self.flush()
        self.line.append((self.cursor_x, text, font))
        self.cursor_x += w

    def flush(self):
        if not self.line:
            return
        metrics = [font.metrics() for _, _, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = HSTEP
        self.line = []
