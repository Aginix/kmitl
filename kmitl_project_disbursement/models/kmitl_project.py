# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError

# Disbursement states that no longer hold the project open: cancelled, or fully
# settled by the finance bridge (paid/cleared). Everything else is "ค้าง".
DISBURSEMENT_SETTLED_STATES = ("cancel", "paid", "cleared")


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    currency_id = fields.Many2one(related="company_id.currency_id")

    # Active (non-cancelled) disbursements — the meaningful figure on the badge.
    disbursement_count = fields.Integer(
        compute="_compute_disbursement_count",
        string="Disbursement Count",
    )
    disbursement_amount = fields.Monetary(
        compute="_compute_disbursement_count",
        string="ยอดส่งเบิก",
        currency_field="currency_id",
    )
    # Cancelled ones, counted separately so they never inflate the active badge.
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
                rec.disbursement_count = 0
                rec.disbursement_amount = 0.0
                rec.disbursement_cancelled_count = 0
                continue
            active_drs = DR.search(rec._disbursement_domain(cancelled=False))
            rec.disbursement_count = len(active_drs)
            rec.disbursement_amount = sum(active_drs.mapped("amount_total"))
            rec.disbursement_cancelled_count = DR.search_count(
                rec._disbursement_domain(cancelled=True)
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

    def action_open_disbursements(self):
        self.ensure_one()
        return {
            "name": _("การเบิกจ่าย"),
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "view_mode": "tree,form",
            "domain": self._disbursement_domain(cancelled=False),
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
            self.env["disbursement.request"].sudo().search_count(
                [
                    ("kmitl_project_analytic_id", "=", self.analytic_account_id.id),
                    ("state", "not in", DISBURSEMENT_SETTLED_STATES),
                ]
            )
        )

    def action_complete(self):
        """Block closing a project that still has an outstanding (ค้าง)
        disbursement — its money is not yet fully accounted for."""
        self.ensure_one()
        if self._has_open_disbursement():
            raise UserError(
                _(
                    "ไม่สามารถปิดโครงการได้ "
                    "เนื่องจากยังมีใบขอเบิกที่ค้างดำเนินการอยู่"
                )
            )
        return super().action_complete()
