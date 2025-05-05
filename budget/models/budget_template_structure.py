import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BudgetTemplateStructure(models.AbstractModel):
    _name = "report.budget.budget_template_structure"
    _description = "Budget Structure"

    @api.model
    def get_html(self, template_id, domain=[]):
        return self._get_data(template_id=template_id, domain=domain)

    @api.model
    def _get_data(self, template_id, domain):
        budget_template = self.env["budget.template"].browse(template_id)
        lines = self._get_budget_structure(budget_template=budget_template)

        return {
            "lines": lines,
            "budget_template": {
                "id": budget_template.id,
                "name": budget_template.name,
            },
        }

    def _get_budget_structure(self, budget_template):
        lines = self._prepare_lines(budget_template)
        return self._flatten_tree(self._build_tree(lines))

    def _build_tree(self, data):
        # สร้าง dictionary เพื่อเก็บโหนดตาม id
        nodes = {}
        for item in data:
            item["children"] = []
            nodes[item["id"]] = item

        # สร้างตัวแปรสำหรับเก็บ root node
        tree = []

        # จัดโครงสร้างตาม parent_id
        for item in data:
            node_id = item["id"]
            parent_id = item["parent_id"]

            # ถ้าไม่มี parent_id (root node)
            if parent_id is None or parent_id is False:
                tree.append(nodes[node_id])
            # ถ้ามี parent_id เพิ่มเข้าไปใน children ของ parent
            elif parent_id in nodes:
                nodes[parent_id]["children"].append(nodes[node_id])

        # เรียงลำดับ children ตาม sequence
        def sort_children(node):
            node["children"] = sorted(node["children"], key=lambda x: x["sequence"])
            for child in node["children"]:
                sort_children(child)

        for root in tree:
            sort_children(root)

        return self._traverse_tree(tree)

    def _traverse_tree(self, tree):
        for root in tree:
            self._traverse_node(root)
        return tree

    def _traverse_node(self, node):
        return node

    # ฟังก์ชัน flatten tree เป็น list
    def _flatten_tree(self, tree):
        flat_list = []

        def traverse(node):
            data = node.copy()
            del data["children"]
            flat_list.append(data)
            for child in node["children"]:  # children ถูกเรียงตาม sequence แล้ว
                traverse(child)

        for root in tree:
            traverse(root)

        return flat_list

    def _prepare_lines(self, budget_template):
        lines = []
        for template_line in budget_template.line_ids:
            lines.append(self._prepare_line(template_line))
        return lines

    def _prepare_line(self, template_line):
        return {
            "id": template_line.id,
            "code": template_line.code,
            "name": template_line.name,
            "sequence": template_line.sequence,
            "has_children": template_line.child_ids.ids,
            "parent_id": template_line.parent_id.id,
            "level": template_line.hierarchy_level,
            "template_id": template_line.template_id.id,
            "parent_path": template_line.parent_path,
            "budget_type": template_line.budget_type,
            "fund_analytic_ids": template_line.fund_analytic_ids.mapped(
                lambda record: {
                    "id": record.id,
                    "code": record.code,
                    "name": record.name,
                    "display_name": record.display_name,
                    "parent_id": record.parent_id.id,
                }
            ),
        }
