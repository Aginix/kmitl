import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class BudgetExpenditureReport(models.AbstractModel):
    _name = "report.budget.budget_expenditure_report"
    _inherit = "report.budget.budget_template_structure"
    _description = "Budget Expenditure Report"

    def _prepare_lines(self, budget_template):
        lines = []
        budget_appropriation_map = self._get_budget_appropriations(budget_template.id)
        budget_commitment_map = self._get_budget_commitments(budget_template.id)
        for template_line in budget_template.line_ids:
            budget_appropriations = budget_appropriation_map.get(template_line.code, [])
            budget_commitments = budget_commitment_map.get(template_line.code, [])
            prepare_line = self._prepare_line(
                template_line,
                budget_appropriations,
                budget_commitments=budget_commitments,
            )
            lines.append(prepare_line)
        return lines

    def _get_budget_appropriations(self, budget_template_id):
        line_map = {}
        lines = self.env["budget.appropriation.line"].search_read(
            [
                "&",
                ["template_id", "=", budget_template_id],
                ["parent_state", "=", "posted"],
            ]
        )

        for line in lines:
            if not line_map.get(line["code"]):
                line_map[line["code"]] = []
            line_map[line["code"]].append(line)

        return line_map

    def _get_budget_commitments(self, budget_template_id):
        line_map = {}
        lines = self.env["budget.commitment.line"].search_read(
            [
                "&",
                ["template_id", "=", budget_template_id],
                ["parent_state", "=", "submitted"],
            ]
        )

        for line in lines:
            if not line_map.get(line["code"]):
                line_map[line["code"]] = []
            line_map[line["code"]].append(line)

        return line_map

    def _prepare_line(
        self,
        template_line,
        budget_appropriations,
        budget_commitments=[],
        budget_reserveds=[],
        budget_obligated=[],
    ):
        line = super()._prepare_line(template_line)
        # (a)
        line["a"] = sum([x["amount"] for x in budget_appropriations])
        # (b)
        line["b"] = sum([x["amount"] for x in budget_commitments])
        # (c)
        line["c"] = sum([x["amount"] for x in budget_reserveds])
        # (d)
        line["d"] = sum([x["amount"] for x in budget_obligated])
        # (e)
        line["e"] = 0
        # (f)
        line["f"] = line["b"] + line["c"] + line["d"] + line["e"]
        # (g)
        line["g"] = line["a"] - line["f"]
        return line

    def _traverse_node(self, node):
        computation_field = {
            "a": 0,
            "b": 0,
            "c": 0,
            "d": 0,
            "e": 0,
            "f": 0,
            "g": 0,
        }
        for child in node["children"]:
            result = self._traverse_node(child)
            computation_field["a"] += result["a"]
            computation_field["b"] += result["b"]
            computation_field["c"] += result["c"]
            computation_field["d"] += result["d"]
            computation_field["e"] += result["e"]
            computation_field["f"] += result["f"]
            computation_field["g"] += result["g"]

        node["a"] += computation_field["a"]
        node["b"] += computation_field["b"]
        node["c"] += computation_field["c"]
        node["d"] += computation_field["d"]
        node["e"] += computation_field["e"]
        node["f"] += computation_field["f"]
        node["g"] += computation_field["g"]
        return {
            "a": node["a"],
            "b": node["b"],
            "c": node["c"],
            "d": node["d"],
            "e": node["e"],
            "f": node["f"],
            "g": node["g"],
        }
