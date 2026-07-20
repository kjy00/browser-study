import sys

from browser import Browser
from url import URL


if __name__ == "__main__":
    browser = Browser()

    def load():
        try:
            browser.load(URL(sys.argv[1]))
        except Exception:
            browser.load(URL("about:blank"))

    browser.window.after(10, load)
    browser.window.mainloop()
