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
        """Only an *approved* project's own slip is drawable. A kmitl.project
        reserves at ``to_verify`` → ``to_send``, i.e. before its own หนังสือ is
        approved (``in_progress``), so a slip alone is no proof of authorisation
        — and the auto-approve that skips e-Saraban leans entirely on that proof
        (agx_approval docs/adr/0005-project-mode-auto-approve-skips-esaraban).

        The approved projects are resolved with ``sudo`` and passed in as ids
        rather than expressed as a ``kmitl_project_id.state`` path: reading
        kmitl.project needs a project group the budget officer picking the slip
        need not have, and the path's sub-search would also apply the
        own-projects record rule — narrowing the dropdown to the picker's own
        projects. Which slips may be seen stays governed by budget.commitment's
        own rules (ADR-0011), unchanged."""
        if self.budget_selection_mode == "project":
            projects = (
                self.env["kmitl.project"]
                .sudo()
                .search([("state", "=", "in_progress")])
            )
            return [
                ("account_id.is_project", "=", True),
                ("kmitl_project_id", "in", projects.ids),
            ]
        return super()._reservation_commitment_mode_domain()

    def _domain_budget_account_id(self):
        # Reserve-new (normal mode) and a category pin can never target a
        # project code — project money is only ever drawn from a slip the
        # project itself already reserved (see _check_drawable_commitment).
        return super()._domain_budget_account_id() + [("is_project", "=", False)]

    def _check_drawable_commitment(self, commitment):
        """The base gate hard-rejects every project-owned slip (drawable only
        through a dedicated create-from-source flow). ``project`` mode is that
        dedicated flow: allow it, checking that the slip genuinely sits on a
        project budget code and that its project is actually approved — the
        category pin and non-procurement baseline that gate ``normal`` mode
        don't apply here
        (agx_approval docs/adr/0005-project-mode-auto-approve-skips-esaraban).

        The project-state gate is repeated here, not left to
        ``_reservation_commitment_mode_domain``: that domain only feeds the
        dropdown, while this is the choke point every draw passes through. Read
        through ``sudo`` for the same reason the domain does — the budget officer
        drawing the slip need not hold a kmitl.project group."""
        if self.budget_selection_mode == "project" and commitment.kmitl_project_id:
            if not commitment.account_id.is_project:
                raise UserError(
                    _(
                        "ใบจองงบประมาณของโครงการต้องผูกกับรหัสงบประมาณที่เป็นโครงการเท่านั้น"
                    )
                )
            project = commitment.kmitl_project_id.sudo()
            if project.state != "in_progress":
                raise UserError(
                    _(
                        "โครงการ %s ยังไม่ได้รับอนุมัติ (หรือไม่ได้อยู่ระหว่างดำเนินการ) "
                        "จึงยังหยิบใบจองงบประมาณของโครงการไปใช้ไม่ได้"
                    )
                    % project.name
                )
            return True
        return super()._check_drawable_commitment(commitment)
