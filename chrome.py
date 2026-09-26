from draw import DrawLine, DrawOutline, DrawRect, DrawText, Rect
from fonts import get_font
from url import URL

NEW_TAB_URL = "https://browser.engineering/"

class Chrome:
    def __init__(self, browser):
        self.browser = browser
        self.font = get_font(20, "normal", "roman")
        self.font_height = self.font.metrics("linespace")
        self.padding = 5
        self.focus = None
        self.address_bar = ""

        self.tabbar_top = 0
        self.tabbar_bottom = self.font_height + 2 * self.padding
        self.urlbar_top = self.tabbar_bottom
        self.urlbar_bottom = self.urlbar_top + self.font_height + 2 * self.padding
        self.bottom = self.urlbar_bottom

        plus_width = self.font.measure("+") + 2 * self.padding
        self.newtab_rect = Rect(
            self.padding, self.padding,
            self.padding + plus_width,
            self.padding + self.font_height)

        back_width = self.font.measure("<") + 2 * self.padding
        self.back_rect = Rect(
            self.padding,
            self.urlbar_top + self.padding,
            self.padding + back_width,
            self.urlbar_bottom - self.padding)

    @property
    def address_rect(self):
        return Rect(
            self.back_rect.right + self.padding,
            self.urlbar_top + self.padding,
            self.browser.width - self.padding,
            self.urlbar_bottom - self.padding)

    def tab_rect(self, i: int): 
        tabs_start = self.newtab_rect.right + self.padding
        tab_width = self.font.measure("Tab X") + 2 * self.padding
        return Rect(
            tabs_start + tab_width * i, self.tabbar_top,
            tabs_start + tab_width * (i + 1), self.tabbar_bottom)

    def paint(self):
        cmds = []
        cmds.append(DrawRect(
            Rect(0, 0, self.browser.width, self.bottom), "white"))
        cmds.append(DrawLine(
            0, self.bottom, self.browser.width, self.bottom, "black", 1))

        cmds.append(DrawOutline(self.newtab_rect, "black", 1))
        cmds.append(DrawText(
            self.newtab_rect.left + self.padding,
            self.newtab_rect.top,
            "+", self.font, "black"))

        for i, tab in enumerate(self.browser.tabs):
            bounds = self.tab_rect(i)
            cmds.append(DrawLine(
                bounds.left, 0, bounds.left, bounds.bottom, "black", 1))
            cmds.append(DrawLine(
                bounds.right, 0, bounds.right, bounds.bottom, "black", 1))
            cmds.append(DrawText(
                bounds.left + self.padding, bounds.top + self.padding,
                "Tab {}".format(i), self.font, "black"))
            if tab == self.browser.active_tab:
                cmds.append(DrawLine(
                    0, bounds.bottom, bounds.left, bounds.bottom, "black", 1))
                cmds.append(DrawLine(
                    bounds.right, bounds.bottom, self.browser.width, bounds.bottom, "black", 1))

        cmds.append(DrawOutline(self.back_rect, "black", 1))
        cmds.append(DrawText(
            self.back_rect.left + self.padding,
            self.back_rect.top,
            "<", self.font, "black"))

        address_rect = self.address_rect
        cmds.append(DrawOutline(address_rect, "black", 1))
        if self.focus == "address bar":
            cmds.append(DrawText(
                address_rect.left + self.padding,
                address_rect.top,
                self.address_bar, self.font, "black"))
            w = self.font.measure(self.address_bar) #입력 위치를 커서로 보여준다.
            cmds.append(DrawLine(
                address_rect.left + self.padding + w, address_rect.top,
                address_rect.left + self.padding + w, address_rect.bottom,
                "red", 1))
        elif self.browser.active_tab is not None:
            url = str(self.browser.active_tab.url)
            cmds.append(DrawText(
                address_rect.left + self.padding,
                address_rect.top,
                url, self.font, "black"))
        return cmds

    def click(self, x, y):
        self.focus = None
        if self.newtab_rect.contains_point(x, y):
            self.browser.new_tab(URL(NEW_TAB_URL))
        elif self.back_rect.contains_point(x, y):
            self.browser.active_tab.go_back()
        elif self.address_rect.contains_point(x, y):
            self.focus = "address bar"
            self.address_bar = ""
        else:
            for i, tab in enumerate(self.browser.tabs):
                if self.tab_rect(i).contains_point(x, y):
                    self.browser.active_tab = tab
                    break

    def keypress(self, char):
        if self.focus == "address bar":
            self.address_bar += char

    def delete(self):
        if self.focus == "address bar":
            self.address_bar = self.address_bar[:-1]

    def enter(self):
        if self.focus == "address bar":
            self.browser.active_tab.load(URL(self.address_bar))
            self.focus = None
