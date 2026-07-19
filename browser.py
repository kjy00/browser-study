import tkinter

from constants import (
    ENTER_STEP,
    HEIGHT,
    HSTEP,
    SCROLLBAR_MIN_HEIGHT,
    SCROLLBAR_WIDTH,
    SCROLL_STEP,
    VSTEP,
    WIDTH,
)
from url import URL


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.width = WIDTH
        self.height = HEIGHT
        self.text = ""
        self.layout_fn = layout_ltr
        self.canvas = tkinter.Canvas(self.window, width=self.width, height=self.height)
        self.canvas.pack(fill="both", expand=True)
        self.scroll = 0
        self.display_list = []
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
        self.display_list = self.layout_fn(self.text, self.width)
        self.draw()

    def load(self, url: URL):
        body = url.request()
        self.text = lex(body)
        if "dir=rtl" in body:
            self.layout_fn = layout_rtl_ar if is_rtl_lang(self.text) else layout_rtl
        else:
            self.layout_fn = layout_ltr
        self.display_list = self.layout_fn(self.text, self.width)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + self.height:
                continue
            if y + VSTEP < self.scroll:
                continue
            self.canvas.create_text(x, y - self.scroll, text=c)
        self.draw_scrollbar()

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


def is_rtl_lang(text: str):
    for c in text:
        if "\u0590" <= c <= "\u05FF" or "\u0600" <= c <= "\u06FF":
            return True
        if "\u0750" <= c <= "\u077F" or "\u08A0" <= c <= "\u08FF":
            return True
    return False


def layout_ltr(text: str, width: int):
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


def layout_rtl(text: str, width: int):
    cursor_x, cursor_y = HSTEP, VSTEP
    display_list = []
    line = []

    def shift_line():
        if not line:
            return
        shift = (width - HSTEP) - line[-1][0]
        for x, y, c in line:
            display_list.append((x + shift, y, c))
        line.clear()

    for c in text:
        if c == "\n":
            shift_line()
            cursor_y += ENTER_STEP
            cursor_x = HSTEP
            continue
        line.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x > width - HSTEP:
            shift_line()
            cursor_x = HSTEP
            cursor_y += VSTEP
    shift_line()
    return display_list


def layout_rtl_ar(text: str, width: int):
    # 아랍어/히브리어 전용
    cursor_x, cursor_y = width - HSTEP, VSTEP
    display_list = []
    for c in text:
        if c == "\n":
            cursor_y += ENTER_STEP
            cursor_x = width - HSTEP
            continue
        display_list.append((cursor_x, cursor_y, c))
        cursor_x -= HSTEP
        if cursor_x < HSTEP:
            cursor_x = width - HSTEP
            cursor_y += VSTEP
    return display_list
