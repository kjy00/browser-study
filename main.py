import os
import sys

import sdl2

from browser import Browser, mainloop
from url import URL

DEFAULT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "default.html")


if __name__ == "__main__":
    sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_EVENTS)
    sdl2.SDL_StartTextInput()
    browser = Browser()

    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = "file://" + DEFAULT_FILE
    try:
        browser.new_window(URL(target))
    except Exception:
        browser.new_window(URL("about:blank"))
    mainloop(browser)
