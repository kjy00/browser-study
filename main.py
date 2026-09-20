import sys

from browser import Browser
from url import URL


if __name__ == "__main__":
    browser = Browser()

    def load():
        try:
            browser.new_tab(URL(sys.argv[1]))
        except Exception:
            browser.new_tab(URL("about:blank"))

    browser.window.after(10, load)
    browser.window.mainloop()
