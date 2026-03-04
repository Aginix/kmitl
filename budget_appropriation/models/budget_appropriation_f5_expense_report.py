import logging

from odoo import _, api, fields, models
from ..utils.tree_builder import BudgetTreeBuilder, TreeConfig, BudgetTreeExporter

_logger = logging.getLogger(__name__)


class BudgetAppropriationF5ExpenseReport(models.AbstractModel):
    _name = "budget.appropriation.f5.expense.report"
    _description = "Budget Appropriation F5 Report"

    @api.model
    def get_report(self, domain):
        accounts = self.env["budget.account"].search([])
        nodes = [LineNode(acc.id, acc.code, acc.name, "account", acc.id, acc.parent_path) for acc in accounts]

        return {
            "domain": domain,
        }


class LineNode:
    def __init__(self, id: str, code: str, name: str, node_type: str, reference: str, parent_path):
        self.id = id
        self.reference = reference
        self.code = code
        self.name = name
        self.node_type = node_type
        self.note = note
        self.amount = 0
        self.parent_path = parent_path

        # Tree Structure
        self.parent = None
        self.children = []
        self.level = 0

    def add_child(self, child: "LineNode") -> "LineNode":
        """Add child node and set relationships"""
        child.parent = self
        child.level = self.level + 1
        self.children.append(child)
        return child

    def to_dict(self):
        return {
            "id": self.id,
            "reference": self.reference,
            "code": self.code,
            "name": self.name,
            "node_type": self.node_type,
            "note": self.note,
            "amount": self.amount,
            # "parent": self.parent,
            # "children": self.children,
            "level": self.level,
        }

    @property
    def amount_total(self):
        total = 0
        for child in self.children:
            total += self.amount_total
        return self.amount + total

    @property
    def get_indent(self):
        return 0


def list_to_tree(data):
    # Create a dictionary to quickly access nodes by their ID
    nodes = {item.id: item for item in data}

    tree = []
    for item in nodes.values():
        parent_id = item.get('parent_id')
        # If the item has a parent and that parent exists in our nodes dictionary,
        # add it as a child to its parent.
        if parent_id and parent_id in nodes and parent_id != item['id']:
            nodes[parent_id]['children'].append(item)
        # Otherwise, if it's a root node (no parent_id or parent_id refers to itself),
        # add it to the main tree list.
        else:
            tree.append(item)
    return tree
