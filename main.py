import os
import sys

from browser import Browser
from url import URL

DEFAULT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "default.html")


if __name__ == "__main__":
    browser = Browser()

    def load():
        if len(sys.argv) > 1:
            target = sys.argv[1]
        else:
            target = "file://" + DEFAULT_FILE
        try:
            browser.new_window(URL(target))
        except Exception:
            browser.new_window(URL("about:blank"))

    browser.root.after(10, load)
    browser.root.mainloop()
