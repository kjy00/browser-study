from layout import Element

INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
}

def tree_to_list(tree, list):
	list.append(tree)
	for child in tree.children:
		tree_to_list(child, list)
	return list

# HTML 트리를 재귀로 돌면서 style 속성을 파싱 후 딕셔너리 형태로 저장
def style(node, rules):
	node.style = {}
	for property, default_value in INHERITED_PROPERTIES.items():
		if node.parent:
			node.style[property] = node.parent.style[property]
		else:
			node.style[property] = default_value
	for selector, body in rules:
		if not selector.matches(node): continue
		for property, value in body.items():
			node.style[property] = value
	if isinstance(node, Element) and "style" in node.attributes:
		pairs = CSSParser(node.attributes["style"]).body()
		for property, value in pairs.items():
			node.style[property] = value
	if node.style["font-size"].endswith("%"):
		if node.parent:
			parent_font_size = node.parent.style["font-size"]
		else:
			parent_font_size = INHERITED_PROPERTIES["font-size"]
		node_pct = float(node.style["font-size"][:-1]) / 100
		parent_px = float(parent_font_size[:-2])
		node.style["font-size"] = str(node_pct * parent_px) + "px"
	for child in node.children:
		style(child, rules)

def cascade_priority(rule): 
	selector, body = rule
	return selector.priority

class CSSParser:
	def __init__(self, s):
		self.s = s
		self.i = 0

	def whitespace(self):
		while self.i < len(self.s) and self.s[self.i].isspace():
			self.i += 1

	def word(self):
		start = self.i
		while self.i < len(self.s):
			if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
				self.i += 1
			else:
				break
		if not (self.i > start):
			raise Exception("Parsing error")
		return self.s[start:self.i]

	def literal(self, literal):
		if not (self.i < len(self.s) and self.s[self.i] == literal):
			raise Exception("Parsing error")
		self.i += 1

	def pair(self):
		prop = self.word()
		self.whitespace()
		self.literal(":")
		self.whitespace()
		val = self.word()
		return prop.casefold(), val

	def body(self):
		pairs = {}
		while self.i < len(self.s):
			try:
				prop, val = self.pair()
				pairs[prop] = val
				self.whitespace()
				self.literal(";")
				self.whitespace()
			except Exception:
				why = self.ignore_until([";", "}"])
				if why == ";":
					self.literal(";")
					self.whitespace()
				else:
					break
		return pairs
	
	def ignore_until(self, chars):
		while self.i < len(self.s):
			if self.s[self.i] in chars:
				return self.s[self.i]
			else:
				self.i += 1
		return None
	
	def selector(self):
		selectors = [TagSelector(self.word().casefold())]
		self.whitespace()
		while self.i < len(self.s) and self.s[self.i] != "{":
			tag = self.word()
			selectors.append(TagSelector(tag.casefold()))
			self.whitespace()
		if len(selectors) == 1:
			return selectors[0]
		return DescendantSelector(selectors)

	def parse(self):
		rules = []
		while self.i <len(self.s):
			try:
				self.whitespace()
				selector = self.selector()
				self.literal("{")
				self.whitespace()
				body = self.body()
				rules.append((selector, body))
			except Exception:
				why = self.ignore_until(["}"])
				if why == "}":
					self.literal("}")
					self.whitespace()
				else:
					break
		return rules

class TagSelector:
	def __init__(self, tag):
		self.tag = tag
		self.priority = 1
	def matches(self, node):
		return isinstance(node, Element) and self.tag == node.tag

class DescendantSelector:
	def __init__(self, selectors):
		self.selectors = selectors
		self.priority = sum(selector.priority for selector in selectors)
	def matches(self, node):
		remaining = self.selectors.copy()
		if not remaining.pop().matches(node):
			return False
		while node.parent and remaining:
			node = node.parent
			if remaining[-1].matches(node):
				remaining.pop()
		return not remaining
