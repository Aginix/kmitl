from odoo import api, models
from odoo.exceptions import ValidationError


class BudgetCommitment(models.Model):
    """Wire the OCA ``base.exception`` framework onto ``budget.commitment``.

    Checked on จองงบ (``action_reserve``). Many flows reserve from code, so a
    blocking rule raises instead of returning a review popup; non-blocking
    rules are only recorded on the slip.
    """

    _name = "budget.commitment"
    _inherit = ["budget.commitment", "base.exception"]
    # Keep the commitment's own ordering over base.exception's.
    _order = "date desc, name desc, id desc"

    @api.model
    def _reverse_field(self):
        return "budget_commitment_ids"

    def _get_base_domain(self):
        # No ignore button: every rule is always evaluated.
        return []

    def action_reserve(self):
        for record in self:
            record.detect_exceptions()
            blocking = record.exception_ids.filtered("is_blocking")
            if blocking:
                raise ValidationError("\n".join(blocking.mapped("name")))
        return super().action_reserve()

    def action_reset_to_draft(self):
        res = super().action_reset_to_draft()
        self.write({"exception_ids": [(5,)]})
        return res
