class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
    
    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x
        if self.previous:
            self.y = self.previous.y + self.previous.height 
        else:
            self.y = self.parent.y 
        for word in self.children:
            word.layout()
        if not self.children:
            self.height = 0
            return
        # Skia ascent는 음수이므로 부호를 뒤집어서 기준선 위에 놓는다.
        max_ascent = max([-word.font.getMetrics().fAscent
                          for word in self.children])
        baseline = self.y + 1.25 * max_ascent
        for word in self.children:
            word.y = baseline + word.font.getMetrics().fAscent
        max_descent = max([word.font.getMetrics().fDescent
                           for word in self.children])
        self.height = 1.25 * (max_ascent + max_descent)

    def should_paint(self):
        return True

    def paint(self):
        return []

    def paint_effects(self, cmds):
        return cmds
