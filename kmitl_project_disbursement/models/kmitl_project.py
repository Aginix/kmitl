# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError

# Disbursement states that no longer hold the project open: cancelled, or fully
# settled by the finance bridge (paid/cleared). Everything else is "ค้าง".
DISBURSEMENT_SETTLED_STATES = ("cancel", "paid", "cleared")

# States before the approval decision (still pending).
DISBURSEMENT_PENDING_STATES = ("draft", "submitted", "signed", "verified")
# States at or after approval (money committed or already paid out).
DISBURSEMENT_DONE_STATES = ("approved", "payment_authorized", "paid", "cleared")


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    currency_id = fields.Many2one(related="company_id.currency_id")

    # Pre-approval disbursements — drafted/submitted but not yet approved.
    disbursement_pending_count = fields.Integer(
        compute="_compute_disbursement_count",
        string="Pending Disbursement Count",
    )
    disbursement_pending_amount = fields.Monetary(
        compute="_compute_disbursement_count",
        string="ยอดรอดำเนินการ",
        currency_field="currency_id",
    )
    # Post-approval disbursements — approved, authorized, paid, or cleared.
    disbursement_done_count = fields.Integer(
        compute="_compute_disbursement_count",
        string="Approved Disbursement Count",
    )
    disbursement_done_amount = fields.Monetary(
        compute="_compute_disbursement_count",
        string="ยอดอนุมัติแล้ว",
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
            pending = DR.search(base + [("state", "in", DISBURSEMENT_PENDING_STATES)])
            done = DR.search(base + [("state", "in", DISBURSEMENT_DONE_STATES)])
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
            "domain": [
                ("kmitl_project_analytic_id", "=", self.analytic_account_id.id),
                ("state", "in", DISBURSEMENT_PENDING_STATES),
            ],
        }

    def action_open_done_disbursements(self):
        self.ensure_one()
        return {
            "name": _("ใบเบิกอนุมัติแล้ว"),
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "view_mode": "tree,form",
            "domain": [
                ("kmitl_project_analytic_id", "=", self.analytic_account_id.id),
                ("state", "in", DISBURSEMENT_DONE_STATES),
            ],
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
