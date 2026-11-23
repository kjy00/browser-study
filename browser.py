import ctypes
import math
import sys
import threading
import urllib.parse
from JSContext import JSContext
import sdl2
import skia

from constants import (
    HEIGHT,
    SCROLLBAR_MIN_HEIGHT,
    SCROLLBAR_WIDTH,
    SCROLL_STEP,
    VSTEP,
    WIDTH,
)
from chrome import NEW_TAB_URL, Chrome
from cssParser import CSSParser, cascade_priority, style, tree_to_list
from documentLayout import DocumentLayout
from blockLayout import Element, HTMLParser, Text, paint_tree
from draw import DrawRect
from url import URL

DEFAULT_STYLE_SHEET = CSSParser(open("browser.css").read()).parse()
# 화면을 다시 그리는 간격. 초당 약 30프레임이다.
REFRESH_RATE_SEC = .033

class Task:
    # 나중에 실행할 함수와 인자. 지금 당장 부르지 않는다.
    def __init__(self, task_code, *args):
        self.task_code = task_code
        self.args = args

    def run(self):
        self.task_code(*self.args)
        self.task_code = None
        self.args = None


class TaskRunner:
    # 탭마다 하나씩. 먼저 넣은 태스크를 먼저 실행한다.
    def __init__(self, tab):
        self.tab = tab
        self.tasks = []
        # 메인 스레드와 타이머 스레드가 이 리스트를 동시에 건드리지 않게 한다.
        self.condition = threading.Condition()

    def schedule_task(self, task):
        self.condition.acquire(blocking=True)
        self.tasks.append(task)
        self.condition.notify_all()
        self.condition.release()

    def run(self):
        task = None
        self.condition.acquire(blocking=True)
        if len(self.tasks) > 0:
            task = self.tasks.pop(0)
        self.condition.release()
        if task:
            task.run()


class Browser:
    #프로세스 전체. 창 목록과 SDL 이벤트만 가진다.
    def __init__(self):
        self.windows = []
        self.windows_by_id = {}

    def new_window(self, url: URL):
        window = Window(self)
        self.windows.append(window)
        self.windows_by_id[window.window_id] = window
        window.new_tab(url)
        sdl2.SDL_RaiseWindow(window.sdl_window)
        return window

    def window_for(self, window_id):
        return self.windows_by_id.get(window_id)

    def close_window(self, window):
        self.windows.remove(window)
        self.windows_by_id.pop(window.window_id, None)
        sdl2.SDL_DestroyWindow(window.sdl_window)
        if not self.windows:
            sdl2.SDL_Quit()
            sys.exit()

    def handle_quit(self):
        for window in list(self.windows):
            sdl2.SDL_DestroyWindow(window.sdl_window)
        self.windows.clear()
        self.windows_by_id.clear()


class Window:
    #창 하나. SDL 창과 크롬, 탭 표면을 가진다.
    def __init__(self, browser: Browser):
        self.browser = browser
        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.width = WIDTH
        self.height = HEIGHT
        self.sdl_window = sdl2.SDL_CreateWindow(
            b"Browser",
            sdl2.SDL_WINDOWPOS_CENTERED,
            sdl2.SDL_WINDOWPOS_CENTERED,
            self.width,
            self.height,
            sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_RESIZABLE)
        if not self.sdl_window:
            message = sdl2.SDL_GetError()
            if isinstance(message, bytes):
                message = message.decode()
            raise RuntimeError(message)
        self.window_id = sdl2.SDL_GetWindowID(self.sdl_window)
        shown_w, shown_h = ctypes.c_int(), ctypes.c_int()
        sdl2.SDL_GetWindowSize(
            self.sdl_window, ctypes.byref(shown_w), ctypes.byref(shown_h))
        self.width = shown_w.value
        self.height = shown_h.value
        self.chrome = Chrome(self)
        self.root_surface = self.make_root_surface()
        self.chrome_surface = skia.Surface(
            self.width, math.ceil(self.chrome.bottom))
        self.tab_surface = None
        self.animation_timer = None
        self.needs_raster_and_draw = False
        if sdl2.SDL_BYTEORDER == sdl2.SDL_BIG_ENDIAN:
            self.RED_MASK = 0xff000000
            self.GREEN_MASK = 0x00ff0000
            self.BLUE_MASK = 0x0000ff00
            self.ALPHA_MASK = 0x000000ff
        else:
            self.RED_MASK = 0x000000ff
            self.GREEN_MASK = 0x0000ff00
            self.BLUE_MASK = 0x00ff0000
            self.ALPHA_MASK = 0xff000000

    def make_root_surface(self):
        return skia.Surface.MakeRaster(
            skia.ImageInfo.Make(
                self.width, self.height,
                ct=skia.kRGBA_8888_ColorType,
                at=skia.kUnpremul_AlphaType))

    @property
    def tab_height(self):
        return self.height - self.chrome.bottom

    def handle_new_window(self):
        self.browser.new_window(URL(NEW_TAB_URL))

    def new_tab(self, url: URL):
        new_tab = Tab(self, self.width, self.tab_height)
        new_tab.load(url)
        self.active_tab = new_tab
        self.tabs.append(new_tab)

    def handle_down(self):
        if self.active_tab is None:
            return
        self.active_tab.scroll_down()
        self.draw()

    def handle_up(self):
        if self.active_tab is None:
            return
        self.active_tab.scroll_up()
        self.draw()

    def handle_mouse_wheel(self, event):
        if self.active_tab is None:
            return
        delta = event.y
        if delta == 0 and hasattr(event, "preciseY"):
            delta = event.preciseY
        if delta > 0:
            self.active_tab.scroll_up()
        elif delta < 0:
            self.active_tab.scroll_down()
        else:
            return
        self.draw()

    def handle_click(self, e):
        if self.active_tab is None:
            return
        if e.y < self.chrome.bottom:
            self.focus = None
            self.chrome.click(e.x, e.y)
            self.set_needs_raster_and_draw()
        else:
            if self.focus != "content":
                self.focus = "content"
                self.chrome.blur()
                self.set_needs_raster_and_draw()
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)

    def handle_key(self, char):
        if len(char) == 0: return
        if not (0x20 <= ord(char) < 0x7f): return
        if self.chrome.keypress(char):
            self.set_needs_raster_and_draw()
        elif self.focus == "content" and self.active_tab is not None:
            self.active_tab.keypress(char)

    def handle_enter(self):
        if self.chrome.enter():
            self.set_needs_raster_and_draw()

    def handle_backspace(self):
        if self.chrome.focus == "address bar":
            self.chrome.delete()
            self.set_needs_raster_and_draw()

    def handle_resize(self, width, height):
        width = int(width)
        height = int(height)
        if width <= 1 or height <= self.chrome.bottom:
            return
        if width == self.width and height == self.height:
            return
        self.width = width
        self.height = height
        self.root_surface = self.make_root_surface()
        self.chrome_surface = skia.Surface(
            self.width, math.ceil(self.chrome.bottom))
        for tab in self.tabs:
            tab.resize(self.width, self.tab_height)
        self.set_needs_raster_and_draw()

    def set_needs_raster_and_draw(self):
        self.needs_raster_and_draw = True

    def raster_and_draw(self):
        if not self.needs_raster_and_draw:
            return
        self.raster_chrome()
        self.raster_tab()
        self.draw()
        self.needs_raster_and_draw = False

    def schedule_animation_frame(self):
        # 이미 기다리는 타이머가 있으면 새로 만들지 않는다. 33ms에 렌더 한 번이다.
        def callback():
            active_tab = self.active_tab
            if active_tab:
                task = Task(active_tab.render)
                active_tab.task_runner.schedule_task(task)
            self.animation_timer = None
        if not self.animation_timer:
            self.animation_timer = threading.Timer(REFRESH_RATE_SEC, callback)
            self.animation_timer.start()

    def raster_tab(self):
        # 페이지가 바뀔 때만 탭 표면을 다시 그린다. 스크롤은 이 표면을 옮기기만 한다.
        tab = self.active_tab
        if tab is None or tab.document is None:
            return
        tab_height = math.ceil(tab.document.height + 2 * VSTEP)
        tab_height = max(tab_height, 1)
        if not self.tab_surface \
                or tab_height != self.tab_surface.height() \
                or self.width != self.tab_surface.width():
            self.tab_surface = skia.Surface(self.width, tab_height)
        canvas = self.tab_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        tab.raster(canvas)

    def raster_chrome(self):
        canvas = self.chrome_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        for cmd in self.chrome.paint():
            cmd.execute(canvas)

    def draw(self):
        self.composite()
        if self.active_tab is None or self.tab_surface is None:
            return
        if self.active_tab.title:
            sdl2.SDL_SetWindowTitle(
                self.sdl_window, self.active_tab.title.encode("utf8"))

        skia_image = self.root_surface.makeImageSnapshot()
        skia_bytes = skia_image.tobytes()
        depth = 32
        pitch = 4 * self.width
        sdl_surface = sdl2.SDL_CreateRGBSurfaceFrom(
            skia_bytes, self.width, self.height, depth, pitch,
            self.RED_MASK, self.GREEN_MASK,
            self.BLUE_MASK, self.ALPHA_MASK)
        rect = sdl2.SDL_Rect(0, 0, self.width, self.height)
        window_surface = sdl2.SDL_GetWindowSurface(self.sdl_window)
        sdl2.SDL_BlitSurface(sdl_surface, rect, window_surface, rect)
        sdl2.SDL_UpdateWindowSurface(self.sdl_window)
        sdl2.SDL_FreeSurface(sdl_surface)

    def composite(self):
        # 탭 표면과 크롬 표면을 루트 표면에 합친다. 스크롤은 탭 표면을 옮기기만 한다.
        if self.active_tab is None or self.tab_surface is None:
            return
        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        tab_rect = skia.Rect.MakeLTRB(
            0, self.chrome.bottom, self.width, self.height)
        tab_offset = self.chrome.bottom - self.active_tab.scroll
        canvas.save()
        canvas.clipRect(tab_rect)
        canvas.translate(0, tab_offset)
        self.tab_surface.draw(canvas, 0, 0)
        canvas.restore()
        self.active_tab.paint_scrollbar(canvas, self.chrome.bottom)
        chrome_rect = skia.Rect.MakeLTRB(0, 0, self.width, self.chrome.bottom)
        canvas.save()
        canvas.clipRect(chrome_rect)
        self.chrome_surface.draw(canvas, 0, 0)
        canvas.restore()


class Tab:
    def __init__(self, window, width: int, tab_height: int):
        self.window = window
        self.width = width
        self.tab_height = tab_height
        self.nodes = None
        self.document = None
        self.scroll = 0
        self.display_list = []
        self.url = None
        self.history = []
        self.title = ""
        self.focus = None
        self.js = None
        self.needs_render = False
        self.task_runner = TaskRunner(self)

    @property
    def doc_height(self):
        if self.document is None:
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
        self.set_needs_render()
        self.render()
        self.scroll = min(self.scroll, self.max_scroll)

    def set_needs_render(self):
        self.needs_render = True

    def click(self, x, y):
        self.render()
        self.focus = None
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
                if self.js.dispatch_event("click", elt): return
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)
            elif elt.tag == "input" :
                if self.js.dispatch_event("click", elt): return
                if self.focus:
                    self.focus.is_focused = False
                self.focus = elt
                elt.is_focused = True
                elt.attributes["value"] = ""
                self.set_needs_render()
                return
            elif elt.tag == "button":
                if self.js.dispatch_event("click", elt): return
                while elt:
                    if elt.tag == "form" and "action" in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent
            elt = elt.parent

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def load(self, url: URL, payload=None):
        headers, body = url.request(self.url, payload)
        self.url = url
        self.history.append(url)
        self.allowed_origins = None
        if "content-security-policy" in headers:
            csp = headers["content-security-policy"].split()
            if len(csp) > 0 and csp[0] == "default-src":
                self.allowed_origins = []
                for origin in csp[1:]:
                    self.allowed_origins.append(URL(origin).origin())
        self.nodes = HTMLParser(body).parse()
        self.rules = DEFAULT_STYLE_SHEET.copy()
        if self.js:
            self.js.discarded = True
        self.js = JSContext(self)
        node_list = tree_to_list(self.nodes, [])
        #<title> 태그의 텍스트를 받아온다.
        title_tag = [node for node in node_list if isinstance(node, Element) and node.tag == "title"]
        if title_tag:
            self.title = "".join(child.text for child in title_tag[0].children if isinstance(child, Text))
        else:
            self.title = str(self.url)
        #<script> 태그의 스크립트를 받아온다.
        scripts = [node.attributes["src"] for node in node_list
                if isinstance(node, Element) and node.tag == "script"
                and "src" in node.attributes]
        for script in scripts:
            script_url = url.resolve(script)
            if not self.allowed_request(script_url):
                print("Blocked script", script, "due to CSP")
                continue
            try:
                header, body = script_url.request(url)
            except:
                continue
            task = Task(self.js.run, script_url, body)
            self.task_runner.schedule_task(task)
        #<link> 태그의 스타일시트를 받아온다.
        links = [node.attributes["href"] for node in node_list
                if isinstance(node, Element) and node.tag == "link"
                and node.attributes.get("rel") == "stylesheet"
                and "href" in node.attributes]
        for link in links:
            style_url = url.resolve(link)
            if not self.allowed_request(style_url):
                print("Blocked style", link, "due to CSP")
                continue
            try:
                header, body = style_url.request(url)
            except Exception:
                continue
            self.rules.extend(CSSParser(body).parse())
        style_nodes = [node for node in node_list #<style> 태그의 스타일을 미리 RULE에 넣는다.
            if isinstance(node, Element) and node.tag == "style"
        ]
        for style_node in style_nodes:
            css = "".join( child.text for child in style_node.children if isinstance(child, Text))
            self.rules.extend(CSSParser(css).parse())
        self.scroll = 0
        self.set_needs_render()

    def allowed_request(self, url):
        return self.allowed_origins == None or \
            url.origin() in self.allowed_origins

    def render(self):
        if not self.needs_render:
            return
        style(self.nodes, (sorted(self.rules, key=cascade_priority))) #각 노드에 스타일을 적용한다.
        self.document = DocumentLayout(self.nodes, width=self.width) #레이아웃 트리(x, y, width, height)를 만든다.
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)
        self.needs_render = False
        self.window.set_needs_raster_and_draw()

    def raster(self, canvas):
        for cmd in self.display_list:
            cmd.execute(canvas)

    def paint_scrollbar(self, canvas, offset):
        if not self.display_list or self.max_scroll == 0:
            return
        scrollbar_height = self.tab_height * self.tab_height / self.doc_height
        scrollbar_height = max(SCROLLBAR_MIN_HEIGHT, min(scrollbar_height, self.tab_height))
        pos_x1 = self.width - SCROLLBAR_WIDTH
        pos_y1 = offset + (self.scroll / self.max_scroll) * (self.tab_height - scrollbar_height)
        pos_x2 = self.width
        pos_y2 = pos_y1 + scrollbar_height
        DrawRect(skia.Rect.MakeLTRB(pos_x1, pos_y1, pos_x2, pos_y2), "blue").execute(canvas)

    def keypress(self, char):
        if self.focus:
            if self.js.dispatch_event("keydown", self.focus): return
            self.focus.attributes["value"] += char
            self.set_needs_render()

    def submit_form(self, elt):
        if self.js.dispatch_event("submit", elt): return
        inputs = [node for node in tree_to_list(elt, []) if isinstance(node, Element) and node.tag == "input" and "name" in node.attributes]
        body = ""
        for input in inputs:
            name = input.attributes["name"]
            value = input.attributes.get("value", "")
            name = urllib.parse.quote(name)
            value = urllib.parse.quote(value)
            body += "&" + name + "=" + value
        body = body[1:]
        url = self.url.resolve(elt.attributes["action"])
        method = elt.attributes.get("method", "get").casefold()
        if method == "post":
            self.load(url, body)
        else:
            separator = "&" if "?" in url.path else "?"
            url.path += separator + body
            self.load(url)


def mainloop(browser):
    event = sdl2.SDL_Event()
    while True:
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                browser.handle_quit()
                sdl2.SDL_Quit()
                sys.exit()
            elif event.type == sdl2.SDL_WINDOWEVENT:
                window = browser.window_for(event.window.windowID)
                if window is None:
                    continue
                if event.window.event == sdl2.SDL_WINDOWEVENT_CLOSE:
                    browser.close_window(window)
                elif event.window.event == sdl2.SDL_WINDOWEVENT_SIZE_CHANGED:
                    window.handle_resize(event.window.data1, event.window.data2)
                elif event.window.event == sdl2.SDL_WINDOWEVENT_EXPOSED:
                    window.draw()
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                window = browser.window_for(event.button.windowID)
                if window:
                    window.handle_click(event.button)
            elif event.type == sdl2.SDL_MOUSEWHEEL:
                window = browser.window_for(event.wheel.windowID)
                if window:
                    window.handle_mouse_wheel(event.wheel)
            elif event.type == sdl2.SDL_KEYDOWN:
                window = browser.window_for(event.key.windowID)
                if window is None:
                    continue
                sym = event.key.keysym.sym
                mod = event.key.keysym.mod
                if sym == sdl2.SDLK_RETURN:
                    window.handle_enter()
                elif sym == sdl2.SDLK_DOWN:
                    window.handle_down()
                elif sym == sdl2.SDLK_UP:
                    window.handle_up()
                elif sym == sdl2.SDLK_BACKSPACE:
                    window.handle_backspace()
                elif sym == sdl2.SDLK_n and (mod & sdl2.KMOD_CTRL):
                    window.handle_new_window()
            elif event.type == sdl2.SDL_TEXTINPUT:
                window = browser.window_for(event.text.windowID)
                if window is None:
                    continue
                text = event.text.text
                if isinstance(text, bytes):
                    text = text.decode("utf8")
                window.handle_key(text.replace("\x00", ""))
        # 사용자 입력을 모두 본 뒤에, 보이는 탭의 태스크를 하나만 실행하고 화면을 갱신한다.
        for window in list(browser.windows):
            if window.active_tab:
                window.active_tab.task_runner.run()
            window.raster_and_draw()
            window.schedule_animation_frame()
