class Context:
    def __init__(self, item):
        self.id: int = item["id"]
        self.type: str = item["type"]
        self._raw_item = item
        self.item = item["item"]
        self.command: str = self.item["command"]
        self.arguments: list[str] = self.item["arguments"]
