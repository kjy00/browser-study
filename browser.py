import tkinter

from constants import ENTER_STEP, HEIGHT, HSTEP, SCROLL_STEP, VSTEP, WIDTH
from url import URL


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.width = WIDTH
        self.height = HEIGHT
        self.text = ""
        self.canvas = tkinter.Canvas(self.window, width=self.width, height=self.height)
        self.canvas.pack(fill="both", expand=True)
        self.scroll = 0
        self.display_list = []
        self.window.bind("<Down>", self.scroll_down)
        self.window.bind("<Up>", self.scroll_up)
        self.window.bind("<MouseWheel>", self.scroll_mouse_wheel)
        self.window.bind("<Configure>", self.on_resize)

    def scroll_down(self, event):
        self.scroll += SCROLL_STEP
        self.draw()

    def scroll_up(self, event):
        self.scroll -= SCROLL_STEP
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
        self.display_list = layout(self.text, self.width)
        self.draw()

    def load(self, url: URL):
        body = url.request()
        self.text = lex(body)
        self.display_list = layout(self.text, self.width)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + self.height:
                continue
            if y + VSTEP < self.scroll:
                continue
            self.canvas.create_text(x, y - self.scroll, text=c)


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


def layout(text: str, width: int):
    cursor_x, cursor_y = HSTEP, VSTEP
    display_list = []
    for c in text:
        if c == "\n":
            cursor_y += ENTER_STEP
            cursor_x = HSTEP
            continue
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x > width - HSTEP:
            cursor_x = HSTEP
            cursor_y += VSTEP
    return display_list
