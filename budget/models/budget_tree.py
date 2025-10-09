from typing import List, Dict, Any, Optional, Callable


class BudgetTree:
    @staticmethod
    def create_node(record):
        if record._name == 'budget.account':
            return TreeNode(
                id=record.id,
                code=record.code,
                name=record.name,
                node_type="account",
                record=record,
                parent_id=record.parent_id.id,
                parent_path=record.parent_path,
                note=record.note,
            )


class TreeNode:
    def __init__(
        self,
        id: str,
        code: str,
        name: str,
        record: Any,
        node_type: str = "account",
        parent_id: Optional[int] = None,
        parent_path: Optional[str] = None,
        note: Optional[str] = None,
    ):
        self.id = id
        self.code = code
        self.name = name
        self.node_type = node_type
        self.record = record
        self.note = note
        self.parent_id = parent_id
        self.parent_path = parent_path

        self.amount = 0

        # Tree Structure
        self.parent = None
        self.children = []
        self.level = 0

    def add_child(self, child: "TreeNode") -> "TreeNode":
        """Add child node and set relationships"""
        child.parent = self
        child.level = self.level + 1
        self.children.append(child)
        return child

    def to_dict(self):
        return {
            "key": self.get_key(),
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "node_type": self.node_type,
            "note": self.note,
            "amount": self.amount,
            "parent_id": self.parent_id,
            "children": list(map(lambda x: x.to_dict(), self.children)),
            "level": self.level,
            "indent": self.indent,
            "_meta": self.get_meta(),
        }

    def get_meta(self):
        return None

    @property
    def amount_total(self):
        total = 0
        for child in self.children:
            total += self.amount_total
        return self.amount + total

    @property
    def indent(self):
        return self.level * 8

    def get_key(self):
        path = []
        current = self
        while current:
            path.insert(0, f"{current.node_type}:{current.id}")
            current = current.parent
        return ",".join(path)
