import tkinter

from constants import (
    HEIGHT,
    SCROLLBAR_MIN_HEIGHT,
    SCROLLBAR_WIDTH,
    SCROLL_STEP,
    VSTEP,
    WIDTH,
)
from chrome import Chrome
from cssParser import CSSParser, cascade_priority, style, tree_to_list
from documentLayout import DocumentLayout
from blockLayout import Element, HTMLParser, Text, paint_tree
from url import URL

DEFAULT_STYLE_SHEET = CSSParser(open("browser.css").read()).parse()

class Browser:
    def __init__(self):
        self.tabs = []
        self.active_tab = None
        self.width = WIDTH
        self.height = HEIGHT
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=self.width, height=self.height, bg="white")
        self.canvas.pack(fill="both", expand=True)
        self.chrome = Chrome(self)
        self.window.bind("<Down>", self.handle_down)
        self.window.bind("<Up>", self.handle_up)
        self.window.bind("<MouseWheel>", self.handle_mouse_wheel)
        self.window.bind("<Configure>", self.handle_resize)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Key>", self.handle_key)
        self.window.bind("<Return>", self.handle_enter)

    @property
    def tab_height(self):
        return self.height - self.chrome.bottom

    def new_tab(self, url: URL):
        new_tab = Tab(self.width, self.tab_height)
        new_tab.load(url)
        self.active_tab = new_tab
        self.tabs.append(new_tab)
        self.draw()

    def handle_down(self, event):
        self.active_tab.scroll_down()
        self.draw()

    def handle_up(self, event):
        self.active_tab.scroll_up()
        self.draw()

    def handle_mouse_wheel(self, event):
        if event.delta > 0:
            self.active_tab.scroll_up()
        else:
            self.active_tab.scroll_down()
        self.draw()

    def handle_click(self, event):
        if event.y < self.chrome.bottom:
            self.chrome.click(event.x, event.y)
        else:
            self.active_tab.click(event.x, event.y - self.chrome.bottom)
        self.draw()

    def handle_key(self, event):
        if len(event.char) == 0: return 
        if not (0x20 <= ord(event.char) < 0x7f): return
        self.chrome.keypress(event.char)
        self.draw()

    def handle_enter(self, event):
        self.chrome.enter()
        self.draw()

    def handle_resize(self, event):
        if event.widget != self.window:
            return
        self.width = event.width
        self.height = event.height
        for tab in self.tabs:
            tab.resize(self.width, self.tab_height)
        self.draw()

    def draw(self):
        self.canvas.delete("all") 
        if self.active_tab is not None:
            self.active_tab.draw(self.canvas, self.chrome.bottom)
        for cmd in self.chrome.paint():
            cmd.execute(0, self.canvas)


class Tab:
    def __init__(self, width: int, tab_height: int):
        self.width = width
        self.tab_height = tab_height
        self.nodes = None
        self.document = None
        self.scroll = 0
        self.display_list = []
        self.url = None
        self.history = []

    @property
    def doc_height(self):
        if self.nodes is None:
            return 0
        return self.document.height + 2 * VSTEP

    @property
    def max_scroll(self):
        return max(0, self.doc_height - self.tab_height)

    def scroll_down(self):
        self.scroll = min(self.scroll + SCROLL_STEP, self.max_scroll)

    def scroll_up(self):
        self.scroll = max(0, self.scroll - SCROLL_STEP)

    def resize(self, width: int, tab_height: int):
        self.width = width
        self.tab_height = tab_height
        if self.nodes is None:
            return
        self.render()
        self.scroll = min(self.scroll, self.max_scroll)

    def click(self, x, y):
        y += self.scroll
        objs = [obj for obj in tree_to_list(self.document, []) 
        if obj.x <= x < obj.x + obj.width 
        and obj.y <= y < obj.y + obj.height]
        if not objs:
            return
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)
            elt = elt.parent

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def load(self, url: URL):
        self.url = url
        self.history.append(url)
        body = url.request()
        self.nodes = HTMLParser(body).parse()
        rules = DEFAULT_STYLE_SHEET.copy() 
        node_list = tree_to_list(self.nodes, [])
        #<link> 태그의 스타일시트를 받아온다.
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
        style_nodes = [node for node in node_list #<style> 태그의 스타일을 미리 RULE에 넣는다.
            if isinstance(node, Element) and node.tag == "style"
        ]
        for style_node in style_nodes:
            css = "".join( child.text for child in style_node.children if isinstance(child, Text))
            rules.extend(CSSParser(css).parse())
        style(self.nodes, (sorted(rules, key=cascade_priority))) #각 노드에 스타일을 적용한다.
        self.scroll = 0
        self.render()

    def render(self):
        self.document = DocumentLayout(self.nodes, width=self.width) #레이아웃 트리(x, y, width, height)를 만든다.
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)

    def draw(self, canvas, offset: int):
        for cmd in self.display_list:
            if cmd.rect.top > self.scroll + self.tab_height: continue
            if cmd.rect.bottom < self.scroll: continue
            cmd.execute(self.scroll - offset, canvas)
        self.draw_scrollbar(canvas, offset)

    def draw_scrollbar(self, canvas, offset: int):
        if not self.display_list or self.max_scroll == 0:
            return

        scrollbar_height = self.tab_height * self.tab_height / self.doc_height
        scrollbar_height = max(SCROLLBAR_MIN_HEIGHT, min(scrollbar_height, self.tab_height))

        pos_x1 = self.width - SCROLLBAR_WIDTH
        pos_y1 = offset + (self.scroll / self.max_scroll) * (self.tab_height - scrollbar_height)
        pos_x2 = self.width
        pos_y2 = pos_y1 + scrollbar_height
        canvas.create_rectangle(pos_x1, pos_y1, pos_x2, pos_y2, fill="blue")
