from odoo import models


class ProjectBudgetLine(models.Model):
    _inherit = "project.budget.line"

    def _get_claimed_amounts(self):
        """Claimed Amount (ADR-0013): Σ ``price_total`` of the DR lines naming
        the line, on DRs that left draft and are not cancelled. sudo: the DRs
        may belong to other requesters."""
        res = super()._get_claimed_amounts()
        if not self.ids:
            return res
        groups = (
            self.env["disbursement.request.line"]
            .sudo()
            .read_group(
                [
                    ("kmitl_project_budget_line_id", "in", self.ids),
                    ("request_id.state", "not in", ("draft", "cancel")),
                ],
                ["price_total"],
                ["kmitl_project_budget_line_id"],
            )
        )
        for group in groups:
            line_id = group["kmitl_project_budget_line_id"][0]
            res[line_id] = res.get(line_id, 0.0) + (group["price_total"] or 0.0)
        return res

    def unlink(self):
        """Draft/cancelled DRs hold no claim (ADR-0013): detach their lines so
        a removed plan line does not hit the restrict FK. Claimed lines still
        refuse."""
        self.env["disbursement.request.line"].sudo().search(
            [
                ("kmitl_project_budget_line_id", "in", self.ids),
                ("request_id.state", "in", ("draft", "cancel")),
            ]
        ).write({"kmitl_project_budget_line_id": False})
        return super().unlink()
