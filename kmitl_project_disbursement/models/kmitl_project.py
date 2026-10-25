from odoo import _, fields, models

# What no longer holds the project open: cancelled, or paid in full (settled or
# booked). Everything else is "ค้าง".
DISBURSEMENT_OPEN_DOMAIN = [
    ("state", "!=", "cancel"),
    ("settlement_stage", "not in", ("settled", "booked")),
]
# Not cancelled, and its budget not consumed yet (the column is NULL until it is).
DISBURSEMENT_PENDING_DOMAIN = [
    ("state", "!=", "cancel"),
    ("budget_consumed_amount", "in", (0, False)),
]
# Not cancelled, and its budget consumed (money committed or already paid out).
DISBURSEMENT_DONE_DOMAIN = [
    ("state", "!=", "cancel"),
    ("budget_consumed_amount", ">", 0),
]


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    currency_id = fields.Many2one(related="company_id.currency_id")

    # Disbursements whose budget is not consumed yet.
    disbursement_pending_count = fields.Integer(
        compute="_compute_disbursement_count",
        string="Pending Disbursement Count",
    )
    disbursement_pending_amount = fields.Monetary(
        compute="_compute_disbursement_count",
        string="ยอดรอดำเนินการ",
        currency_field="currency_id",
    )
    # Disbursements whose budget the consume act has consumed (and what follows).
    disbursement_done_count = fields.Integer(
        compute="_compute_disbursement_count",
        string="Consumed Disbursement Count",
    )
    disbursement_done_amount = fields.Monetary(
        compute="_compute_disbursement_count",
        string="ยอดตัดงบแล้ว",
        currency_field="currency_id",
    )
    # Cancelled ones, counted separately so they never inflate the active badges.
    disbursement_cancelled_count = fields.Integer(
        compute="_compute_disbursement_count",
        string="Cancelled Disbursement Count",
    )

    def _compute_disbursement_count(self):
        # sudo so the amount/count shows even to users who lack disbursement.request
        # read access — the access check fires when they actually click through.
        DR = self.env["disbursement.request"].sudo()
        for rec in self:
            if not rec.analytic_account_id:
                rec.disbursement_pending_count = 0
                rec.disbursement_pending_amount = 0.0
                rec.disbursement_done_count = 0
                rec.disbursement_done_amount = 0.0
                rec.disbursement_cancelled_count = 0
                continue
            base = [("kmitl_project_analytic_id", "=", rec.analytic_account_id.id)]
            pending = DR.search(base + DISBURSEMENT_PENDING_DOMAIN)
            done = DR.search(base + DISBURSEMENT_DONE_DOMAIN)
            rec.disbursement_pending_count = len(pending)
            rec.disbursement_pending_amount = sum(pending.mapped("amount_total"))
            rec.disbursement_done_count = len(done)
            rec.disbursement_done_amount = sum(done.mapped("amount_total"))
            rec.disbursement_cancelled_count = DR.search_count(
                base + [("state", "=", "cancel")]
            )

    def _disbursement_domain(self, cancelled=None):
        """Disbursements raised under this project — those carrying the project's
        own ``kmitl_project`` analytic account (unique per project, minted once).
        ``cancelled``: None = all, True = only cancelled, False = only active."""
        self.ensure_one()
        domain = [("kmitl_project_analytic_id", "=", self.analytic_account_id.id)]
        if cancelled is True:
            domain.append(("state", "=", "cancel"))
        elif cancelled is False:
            domain.append(("state", "!=", "cancel"))
        return domain

    def action_open_pending_disbursements(self):
        self.ensure_one()
        return {
            "name": _("ใบเบิกรอดำเนินการ"),
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "view_mode": "tree,form",
            "domain": [("kmitl_project_analytic_id", "=", self.analytic_account_id.id)]
            + DISBURSEMENT_PENDING_DOMAIN,
        }

    def action_open_done_disbursements(self):
        self.ensure_one()
        return {
            "name": _("ใบเบิกตัดงบแล้ว"),
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "view_mode": "tree,form",
            "domain": [("kmitl_project_analytic_id", "=", self.analytic_account_id.id)]
            + DISBURSEMENT_DONE_DOMAIN,
        }

    def action_open_cancelled_disbursements(self):
        self.ensure_one()
        return {
            "name": _("การเบิกจ่ายที่ยกเลิก"),
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "view_mode": "tree,form",
            "domain": self._disbursement_domain(cancelled=True),
        }

    def _has_open_disbursement(self):
        """True when the project still has a disbursement that is neither
        cancelled nor fully settled — it must not be closed while one is ค้าง."""
        self.ensure_one()
        if not self.analytic_account_id:
            return False
        return bool(
            self.env["disbursement.request"]
            .sudo()
            .search_count(
                [("kmitl_project_analytic_id", "=", self.analytic_account_id.id)]
                + DISBURSEMENT_OPEN_DOMAIN
            )
        )

    def _get_open_downstream_documents(self):
        """An outstanding (ค้าง) disbursement keeps the project from being
        closed or deleted — its money is not yet fully accounted for."""
        res = super()._get_open_downstream_documents()
        if self._has_open_disbursement():
            res.append(_("ใบขอเบิกที่ค้างดำเนินการอยู่"))
        return res

    def _get_project_claims(self):
        """The ใบขอเบิก total its cap holds within ``budget_amount``
        (``_exceeds_project_budget``)."""
        res = super()._get_project_claims()
        disbursements = (
            self.env["disbursement.request"]
            .sudo()
            .search([("kmitl_project_id", "=", self.id), ("state", "!=", "cancel")])
        )
        res.append((_("ใบขอเบิก"), sum(disbursements.mapped("amount_total"))))
        return res
