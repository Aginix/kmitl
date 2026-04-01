# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class WorkAcceptance(models.Model):
    _name = "work.acceptance"
    _inherit = ["work.acceptance", "thai.date.mixin"]
    _tier_validation_manual_config = True  # We need more buttons

    wa_tier_validation = fields.Boolean(
        string="Paperless WA",
        readonly=True,
        default=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
        help="If checked, WA created will be approved by committee by tier valiation."
        "Each committee will be notified (by email or inbox) to approve WA.\n"
        "If not checked, WA will be approved by paper outside Odoo, "
        "and the result of WA will be filled in by procurement officer",
    )
    work_acceptance_committee_ids = fields.One2many(
        comodel_name="work.acceptance.committee",
        inverse_name="wa_id",
        string="Work Acceptance Committees",
        copy=True,
    )
    completeness = fields.Float(
        string="Progress",
        compute="_compute_completeness",
        store=True,
    )
    requested_delivery_date = fields.Datetime(
        string="Requested Delivery Date",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    # Late Fines
    late_days = fields.Integer(
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
        help="Late day(s) from Received Date - Due Date",
    )

    fines_rate = fields.Monetary(
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
        help="Default fines per day. Can be overwritten",
    )

    fines_late = fields.Monetary(
        string="Fines Amount",
        tracking=True,
        compute="_compute_fines_late",
        store=True
    )

    price_subtotal = fields.Monetary(
        compute="_compute_price_subtotal",
        string="Project value",
        store=True,
    )

    fines_total = fields.Monetary(
        string="Total",
        compute="_compute_fines_total",
        store=True,
    )

    _sql_constraints = [
        ("late_days", "CHECK (late_days>=0)", "Wrong Late Days, it must be positive!"),
        (
            "fines_rate",
            "CHECK (fines_rate>=0)",
            "Wrong Fines Rate, it must be positive!",
        ),
        (
            "fines_late",
            "CHECK (fines_late>=0)",
            "Wrong Fines Amount, it must be positive!",
        ),
    ]
    
    @api.depends("work_acceptance_committee_ids.status")
    def _compute_completeness(self):
        for rec in self:
            committees = len(rec.work_acceptance_committee_ids)
            rec.completeness = 0
            if committees:
                reviewed = len(rec.work_acceptance_committee_ids.filtered("status"))
                rec.completeness = reviewed / committees * 100

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        res.extend(["work_acceptance_committee_ids"])
        return res

    def _clear_data_committee(self):
        """Clear data work acceptance committee"""
        self.mapped("work_acceptance_committee_ids").write(
            {
                "status": "",
                "note": "",
            }
        )

    def button_draft(self):
        self._clear_data_committee()
        return super().button_draft()

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_id:
            return

        return {
            "name": _("Purchase Order"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "res_id": self.purchase_id.id,
            "view_mode": "form",
            "view_type": "form",
            "target": "current",
            "context": self.env.context,
        }
    
    # Late Fines
    @api.onchange("late_days")
    def _onchange_late_days_negative(self):
        if self.late_days < 0:
            self.late_days = 0

    @api.onchange("requested_delivery_date", "date_due")
    def _onchange_late_days(self):
        late_days = 0
        if self.requested_delivery_date and self.date_due:
            late_days = (self.requested_delivery_date - self.date_due).days
        self.late_days = late_days > 0 and late_days or 0

    @api.onchange("fines_rate")
    def _onchange_fines_rate(self):
        if self.fines_rate < 0:
            self.fines_rate = 0
    
    @api.depends("late_days", "fines_rate")
    def _compute_fines_late(self):
        for rec in self:
            rec.fines_late = rec.late_days * rec.fines_rate

    @api.depends("price_subtotal", "fines_late")
    def _compute_fines_total(self):
        for rec in self:
            result = rec.price_subtotal - rec.fines_late
            rec.fines_total = max(result, 0)

    @api.depends("wa_line_ids", "wa_line_ids.price_subtotal")
    def _compute_price_subtotal(self):
        for rec in self:
            rec.price_subtotal = sum(rec.wa_line_ids.mapped("price_subtotal"))
