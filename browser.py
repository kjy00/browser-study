import tkinter

from constants import (
    HEIGHT,
    SCROLLBAR_MIN_HEIGHT,
    SCROLLBAR_WIDTH,
    SCROLL_STEP,
    VSTEP,
    WIDTH,
)
from cssParser import CSSParser, cascade_priority, style, tree_to_list
from documentLayout import DocumentLayout
from layout import Element, HTMLParser, Text, paint_tree
from url import URL

DEFAULT_STYLE_SHEET = CSSParser(open("browser.css").read()).parse()

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.width = WIDTH
        self.height = HEIGHT
        self.nodes = None
        self.canvas = tkinter.Canvas(self.window, width=self.width, height=self.height, bg="white")
        self.canvas.pack(fill="both", expand=True)
        self.scroll = 0
        self.display_list = []
        self.emoji_image = tkinter.PhotoImage(file="1F600_color.png")
        self.window.bind("<Down>", self.scroll_down)
        self.window.bind("<Up>", self.scroll_up)
        self.window.bind("<MouseWheel>", self.scroll_mouse_wheel)
        self.window.bind("<Configure>", self.on_resize)

    @property
    def doc_height(self):
        if self.nodes is None:
            return 0
        return self.document.height + 2 * VSTEP

    @property
    def max_scroll(self):
        return max(0, self.doc_height - self.height)

    def scroll_down(self, event):
        self.scroll = min(self.scroll + SCROLL_STEP, self.max_scroll)
        self.draw()

    def scroll_up(self, event):
        if self.scroll <= 0:
            return
        self.scroll = max(0, self.scroll - SCROLL_STEP)
        self.draw()

    def scroll_mouse_wheel(self, event):
        if event.delta > 0:
            self.scroll_up(event)
        else:
            self.scroll_down(event)

    def on_resize(self, event):
        if event.widget != self.window:
            return
        self.width = event.width
        self.height = event.height
        if self.nodes is None:
            return
        self.document = DocumentLayout(self.nodes, width=self.width)
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)
        self.scroll = min(self.scroll, self.max_scroll)
        self.draw()

    def load(self, url: URL):
        body = url.request()
        self.nodes = HTMLParser(body).parse()
        rules = DEFAULT_STYLE_SHEET.copy()
        node_list = tree_to_list(self.nodes, [])
        links = [node.attributes["href"] for node in node_list
                if isinstance(node, Element) and node.tag == "link" 
                and node.attributes.get("rel") == "stylesheet" 
                and "href" in node.attributes]
        for link in links:
            style_url = url.resolve(link)
            try:
                body = style_url.request()
            except Exception:
                continue
            rules.extend(CSSParser(body).parse())
        style_nodes = [node for node in node_list 
            if isinstance(node, Element) and node.tag == "style"
        ]
        for style_node in style_nodes:
            css = "".join( child.text for child in style_node.children if isinstance(child, Text))
            rules.extend(CSSParser(css).parse())
        style(self.nodes, (sorted(rules, key=cascade_priority)))
        self.document = DocumentLayout(self.nodes, width=self.width)
        self.document.layout()
        self.scroll = 0
        self.display_list = []
        paint_tree(self.document, self.display_list)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for cmd in self.display_list:
            if cmd.top > self.scroll + self.height: continue
            if cmd.bottom < self.scroll: continue
            cmd.execute(self.scroll, self.canvas)
        self.draw_scrollbar()
        # self.draw_imoji()

    def draw_scrollbar(self):
        if not self.display_list or self.max_scroll == 0:
            return

        scrollbar_height = self.height * self.height / self.doc_height
        scrollbar_height = max(SCROLLBAR_MIN_HEIGHT, min(scrollbar_height, self.height))

        pos_x1 = self.width - SCROLLBAR_WIDTH
        pos_y1 = (self.scroll / self.max_scroll) * (self.height - scrollbar_height)
        pos_x2 = self.width
        pos_y2 = pos_y1 + scrollbar_height
        self.canvas.create_rectangle(pos_x1, pos_y1, pos_x2, pos_y2, fill="blue")

