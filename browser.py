import tkinter

from constants import (
    HEIGHT,
    SCROLLBAR_MIN_HEIGHT,
    SCROLLBAR_WIDTH,
    SCROLL_STEP,
    VSTEP,
    WIDTH,
)
from layout import HTMLParser, Layout, Element, Text
from url import URL


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.width = WIDTH
        self.height = HEIGHT
        self.nodes = None
        self.canvas = tkinter.Canvas(self.window, width=self.width, height=self.height)
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
        if not self.display_list:
            return 0
        return self.display_list[-1][1] + VSTEP

    @property
    def max_scroll(self):
        return max(0, self.doc_height - self.height)

    def scroll_down(self, event):
        if not self.display_list:
            return
        if self.scroll + SCROLL_STEP >= self.max_scroll:
            self.scroll = self.max_scroll
        else:
            self.scroll += SCROLL_STEP
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
        self.display_list = Layout(self.nodes, width=self.width).display_list
        self.scroll = min(self.scroll, self.max_scroll)
        self.draw()

    def load(self, url: URL):
        body = url.request()
        self.nodes = HTMLParser(body).parse()
        self.display_list = Layout(self.nodes, width=self.width).display_list
        self.scroll = 0
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, word, font in self.display_list:
            if y > self.scroll + self.height:
                continue
            if y + VSTEP < self.scroll:
                continue
            self.canvas.create_text(
                x, y - self.scroll, text=word, font=font, anchor="nw"
            )
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

