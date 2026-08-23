import tkinter
import tkinter.font

from draw import DrawRect, DrawText
from constants import HSTEP, VSTEP

FONTS = {}

SELF_CLOSING_TAGS = [
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
]

BLOCK_ELEMENTS = [
    "html", "body", "article", "section","nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]

def is_block_node(node):
    return isinstance(node, Element) and node.tag in BLOCK_ELEMENTS

def paint_tree(layout_object, display_list):
        display_list.extend(layout_object.paint())
        for child in layout_object.children:
            paint_tree(child, display_list)

def get_font(size: int, weight: str, style: str):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]


class Text:
    def __init__(self, text: str, parent):
        self.parent = parent
        self.text = text
        self.children = []
    def __repr__(self):
        return repr(self.text)


class Element:
    def __init__(self, tag: str, attributes, parent):
        self.tag = tag
        self.children = []
        self.parent = parent
        self.attributes = attributes
    def __repr__(self):
        return "<" + self.tag + ">"

class HTMLParser:
    HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript",
        "link", "meta", "title", "style", "script",
    ]
    def __init__(self, body):
        self.body = body
        self.unfinished = []

    def add_text(self, text):
        if text.isspace(): return
        self.implicit_tags(None)
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)
        
    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"): return
        self.implicit_tags(tag)
        if tag.startswith("/"):
            if len(self.unfinished) == 1:
                return
            name = tag[1:]
            if name not in [node.tag for node in self.unfinished]:
                return
            reopen = []
            while self.unfinished[-1].tag != name:
                node = self.unfinished.pop()
                self.unfinished[-1].children.append(node)
                reopen.append(node)
            node = self.unfinished.pop()
            self.unfinished[-1].children.append(node)
            while reopen:
                old = reopen.pop()
                parent = self.unfinished[-1]
                self.unfinished.append(Element(old.tag, old.attributes, parent))
        elif tag in SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)

    def finish(self):
        if not self.unfinished:
            self.implicit_tags(None)
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()

    def parse(self):
        buffer = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if buffer:
                    self.add_text(buffer)
                buffer = ""
            elif c == ">":
                in_tag = False
                self.add_tag(buffer)
                buffer = ""
            else:
                buffer += c
        if not in_tag and buffer:
            self.add_text(buffer)
        return self.finish()

    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break

    def get_attributes(self, text):
        parts = text.split()
        tag = parts[0].casefold()
        attributes = {}
        for attr_pair in parts[1:]:
            if "=" in attr_pair:
                key, value = attr_pair.split("=", 1)
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
                attributes[key.casefold()] = value
            else:
                attributes[attr_pair.casefold()] = ""
        return tag, attributes

def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

class BlockLayout:
    def __init__(self, nodes, parent, previous):
        self.nodes = nodes
        if not isinstance(self.nodes, list):
            self.nodes = [self.nodes]
        self.parent = parent
        self.previous = previous
        self.children = []
        self.display_list = []
        self.width = None
        self.height = None
        self.x = None
        self.y = None

    def paint(self):
        cmds = []
        if len(self.nodes) == 1 and isinstance(self.nodes[0], Element) and self.nodes[0].tag == "pre":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, "gray")
            cmds.append(rect)
        if self.layout_mode() == "inline":
            for x, y, word, font in self.display_list:
                cmds.append(DrawText(x, y, word, font))
        return cmds

    def layout_mode(self):
        if len(self.nodes) > 1:
            # node가 여러개인 경우 inline 모드만 들어오도록 구현한다.
            return "inline"
        if isinstance(self.nodes[0], Text):
            return "inline"
        elif any(isinstance(child, Element) \
            and child.tag in BLOCK_ELEMENTS for child in self.nodes[0].children):
            return "block"
        elif self.nodes[0].children:
            return "inline"
        else:
            return "block"

    def layout(self):
        mode = self.layout_mode()
        self.x = self.parent.x
        self.width = self.parent.width
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        if mode == "block":
            previous = None
            inline_buffer = []
            for child in self.nodes[0].children:
                if not is_block_node(child): #inline tag인 경우
                    inline_buffer.append(child)
                else: #block tag인 경우
                    if inline_buffer: #inline buffer에 쌓인 inline tag를 처리
                        next = BlockLayout(inline_buffer, self, previous)
                        self.children.append(next)
                        inline_buffer = []
                        previous = next
                    next = BlockLayout(child, self, previous)
                    self.children.append(next)
                    previous = next
            if inline_buffer: #남은 inline tag를 처리
                next = BlockLayout(inline_buffer, self, previous)
                self.children.append(next)
                inline_buffer = []
        else:
            self.cursor_x = 0
            self.cursor_y = 0
            self.size = 12
            self.weight = "normal"
            self.style = "roman"
            self.abbr = False
            self.line = []
            self.display_list = []
            self.recurse(self.nodes)
            self.flush()
        for child in self.children:
            child.layout()
        if mode == "block":
            self.height = sum([child.height for child in self.children])
        else:
            self.height = self.cursor_y
    def open_tag(self, tag):
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "abbr":
            self.abbr = True
        
        elif tag == "br":
            self.flush()
    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "abbr":
            self.abbr = False
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP

    def recurse(self, tree):
        for node in tree:
            if isinstance(node, Text):
                for word in node.text.split():
                    self.word(word)
            else:
                self.open_tag(node.tag)
                self.recurse(node.children)
                self.close_tag(node.tag)

    def word(self, word):
        font = get_font(self.size, self.weight, self.style)
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
        if self.cursor_x + w > self.width:
            self.flush()
        self.line.append((self.cursor_x, text, font))
        self.cursor_x += w

    def flush(self):
        if not self.line:
            return
        self.cursor_x = 0
        metrics = [font.metrics() for _, _, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        for rel_x, word, font in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = 0
        self.line = []
