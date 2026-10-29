# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models

# ส่งคืนผู้จัดทำ markers. The send-back links them itself and any later state
# change clears them. Detection never evaluates them: it would unlink them, and
# pop them up on the very resubmission that should clear them.
SENT_BACK_RULE = "disbursement_return_exception.excep_disbursement_sent_back"


class DisbursementRequest(models.Model):
    """A request sent back to its maker shows ส่งคืนผู้จัดทำ in ข้อผิดพลาด until
    it is resubmitted."""

    _inherit = "disbursement.request"

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

    def _action_return_for_edit(self, reason):
        res = super()._action_return_for_edit(reason)
        # Only the requests sent back to their maker (draft), not to a source.
        self.filtered(lambda r: r.state == "draft").exception_ids = [
            (4, self.env.ref(SENT_BACK_RULE).id)
        ]
        return res
