from draw import DrawRect, Rect
from constants import HSTEP, VSTEP
from fonts import get_font
from inputLayout import INPUT_WIDTH_PX, InputLayout
from lineLayout import LineLayout
from textLayout import TextLayout



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
    if layout_object.should_paint():
        display_list.extend(layout_object.paint())
    for child in layout_object.children:
        paint_tree(child, display_list)



class Text:
    def __init__(self, text: str, parent):
        self.parent = parent
        self.text = text
        self.children = []
        self.is_focused = False
    def __repr__(self):
        return repr(self.text)


class Element:
    def __init__(self, tag: str, attributes, parent):
        self.tag = tag
        self.children = []
        self.parent = parent
        self.attributes = attributes
        self.is_focused = False
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
        self.width = None
        self.height = None
        self.x = None
        self.y = None

    def self_rect(self):
        return Rect(self.x, self.y,
            self.x + self.width, self.y + self.height)

    def paint(self):
        cmds = []
        if len(self.nodes) == 1:
            bgColor = self.nodes[0].style.get("background-color", "transparent")
        else:
            bgColor = "transparent"
        if bgColor != "transparent":
            rect = DrawRect(self.self_rect(), bgColor)
            cmds.append(rect)
        return cmds

    def should_paint(self):
        return isinstance(self.nodes[0], Text) or (self.nodes[0].tag != "input" and self.nodes[0].tag != "button")

    def layout_mode(self):
        if len(self.nodes) > 1:
            # node가 여러개인 경우 inline 모드만 들어오도록 구현한다.
            return "inline"
        if isinstance(self.nodes[0], Text):
            return "inline"
        elif any(isinstance(child, Element) \
            and child.tag in BLOCK_ELEMENTS for child in self.nodes[0].children):
            return "block"
        elif self.nodes[0].children or self.nodes[0].tag == "input":
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
            run_in = None
            for child in self.nodes[0].children:
                if not is_block_node(child): #inline tag인 경우
                    if run_in: #대기 중인 run-in은 인라인 흐름 맨 앞에 합류시킨다
                        inline_buffer.append(run_in)
                        run_in = None
                    inline_buffer.append(child)
                else: #block tag인 경우
                    if inline_buffer: #inline buffer에 쌓인 inline tag를 처리
                        next = BlockLayout(inline_buffer, self, previous)
                        self.children.append(next)
                        inline_buffer = []
                        previous = next
                    if child.tag == "h6":
                        run_in = child
                        continue
                    if run_in:
                        next = BlockLayout([run_in, child], self, previous)
                        run_in = None
                    else:
                        next = BlockLayout(child, self, previous)
                    self.children.append(next)
                    previous = next
            if inline_buffer: #남은 inline tag를 처리
                next = BlockLayout(inline_buffer, self, previous)
                self.children.append(next)
                inline_buffer = []
            if run_in:
                next = BlockLayout(run_in, self, previous)
                self.children.append(next)
                run_in = None
        else:
            self.cursor_x = 0
            self.new_line()
            self.recurse(self.nodes)
        for child in self.children:
            child.layout()
        self.height = sum([child.height for child in self.children])

    def recurse(self, tree):
        for node in tree:
            if isinstance(node, Text):
                for word in node.text.split():
                    self.word(node, word)
            else:
                if node.tag == "br":
                    self.new_line()
                elif node.tag == "input" or node.tag == "button":
                    self.input(node)
                self.recurse(node.children)

    def input(self, node):
        w = INPUT_WIDTH_PX
        if self.cursor_x + w > self.width:
            self.new_line()
        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        input = InputLayout(node, line, previous_word)
        line.children.append(input)

        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = get_font(size, weight, style)
        self.cursor_x += w + font.measure(" ")

    def word(self, node, word):
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal":
            style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = get_font(size, weight, style)
        w = font.measure(word)
        if self.cursor_x + w > self.width:
            self.new_line()
        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        text = TextLayout(node, word, line, previous_word)
        line.children.append(text)
        self.cursor_x += w + font.measure(" ")

    def new_line(self):
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.nodes[0], self, last_line)
        self.children.append(new_line)
