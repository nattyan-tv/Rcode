from typing import Any

class Context:
    def __init__(self, item: dict[str, Any]):
        self.type: str = item["type"]
        self._raw_item = item
        self.item: dict[str, Any] = item["item"]
        self.command: str = self.item["command"]
        self.arguments: dict[str, str | int | list[str | int] | None] = self.item["arguments"]
