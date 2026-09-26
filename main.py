import sys

from browser import Browser
from url import URL


if __name__ == "__main__":
    browser = Browser()

    def load():
        try:
            browser.new_window(URL(sys.argv[1]))
        except Exception:
            browser.new_window(URL("about:blank"))

    browser.root.after(10, load)
    browser.root.mainloop()
