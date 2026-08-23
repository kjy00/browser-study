from constants import HSTEP, VSTEP
from layout import BlockLayout


class DocumentLayout:
    def __init__(self, node, width: int):
        self.node = node
        self.parent = None
        self.children = []
        self.width = width - 2 * HSTEP
    def layout(self):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        self.x = HSTEP
        self.y = VSTEP
        child.layout()
        self.height = child.height
    def paint(self):
        return []
