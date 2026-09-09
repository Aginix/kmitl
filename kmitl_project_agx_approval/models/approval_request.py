# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    budget_selection_mode = fields.Selection(
        selection_add=[("project", "โครงการ/กิจกรรม")],
        ondelete={"project": "set default"},
    )

    def _reservation_commitment_mode_domain(self):
        if self.budget_selection_mode == "project":
            return [("account_id.is_project", "=", True)]
        return super()._reservation_commitment_mode_domain()

    def _domain_budget_account_id(self):
        # Reserve-new (normal mode) and a category pin can never target a
        # project code — project money is only ever drawn from a slip the
        # project itself already reserved (see _check_drawable_commitment).
        return super()._domain_budget_account_id() + [("is_project", "=", False)]

    def _check_drawable_commitment(self, commitment):
        """The base gate hard-rejects every project-owned slip (drawable only
        through a dedicated create-from-source flow). ``project`` mode is that
        dedicated flow: allow it, checking only that the slip genuinely sits on
        a project budget code — the category pin and non-procurement baseline
        that gate ``normal`` mode don't apply here
        (agx_approval docs/adr/0005-project-mode-auto-approve-skips-esaraban)."""
        if self.budget_selection_mode == "project" and commitment.kmitl_project_id:
            if not commitment.account_id.is_project:
                raise UserError(
                    _(
                        "ใบจองงบประมาณของโครงการต้องผูกกับรหัสงบประมาณที่เป็นโครงการเท่านั้น"
                    )
                )
            return True
        return super()._check_drawable_commitment(commitment)
