from odoo import models

# ส่งกลับแก้ไข markers. The send-back links them itself and any later state
# change clears them. Detection never evaluates them: it would unlink them, and
# pop them up on the very resubmission that should clear them.
SENT_BACK_RULE = "advance_payment_return_exception.excep_advance_payment_sent_back"


class AdvancePayment(models.Model):
    """A loan sent back to its borrower shows ส่งกลับแก้ไข in its exceptions
    until it is resubmitted."""

    _inherit = "advance.payment"

    def _sent_back_rules(self):
        """The marker rules a send-back may link; extend with ``super()``."""
        rule = self.env.ref(SENT_BACK_RULE, raise_if_not_found=False)
        # Not loaded yet while the module installs or upgrades.
        return rule or self.env["exception.rule"]

    def _rule_domain(self):
        # tuple: base_exception caches rules keyed on the (hashable) domain
        return super()._rule_domain() + [
            ("id", "not in", tuple(self._sent_back_rules().ids))
        ]

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals:
            rules = self._sent_back_rules()
            marked = self.filtered(lambda r: r.exception_ids & rules)
            if marked:
                marked.write({"exception_ids": [(3, rule.id) for rule in rules]})
        return res

    def _on_sent_back(self):
        res = super()._on_sent_back()
        # An earlier "ignore" would hide the marker and skip the next checks.
        self.write(
            {
                "ignore_exception": False,
                "exception_ids": [(4, self.env.ref(SENT_BACK_RULE).id)],
            }
        )
        return res
