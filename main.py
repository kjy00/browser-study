import sys

from browser import Browser
from url import URL


if __name__ == "__main__":
    browser = Browser()
    browser.window.after(10, lambda: browser.load(URL(sys.argv[1])))
    browser.window.mainloop()
