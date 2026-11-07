from odoo import fields, models


class ProjectBudgetLine(models.Model):
    _inherit = "project.budget.line"

    # The live project's line a Revision Draft line was copied from: approval
    # updates that line in place, so DR lines naming it stay linked (ADR-0014).
    origin_line_id = fields.Many2one(
        "project.budget.line",
        string="รายการเดิม",
        copy=False,
        readonly=True,
        index=True,
        ondelete="set null",
    )

    def _get_claimed_amounts(self):
        """A draft line shows what was claimed on its live line."""
        res = super()._get_claimed_amounts()
        copies = self.filtered("origin_line_id")
        if copies:
            origin = copies.origin_line_id._get_claimed_amounts()
            for line in copies:
                res[line.id] = origin.get(line.origin_line_id.id, 0.0)
        return res
