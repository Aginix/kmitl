# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    # -- Classification --
    procurement_type_id = fields.Many2one(
        comodel_name="procurement.type",
        string="Procurement Type",
        ondelete="restrict",
        index=True,
    )
    purchase_type_id = fields.Many2one(
        comodel_name="purchase.type",
        string="Purchase Type",
        ondelete="restrict",
        index=True,
        domain=lambda self: self._get_domain_purchase_type(),
        default=lambda self: self.env["purchase.type"].search(
            [("is_default", "=", True)], limit=1
        ),
    )
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        ondelete="restrict",
        index=True,
    )
    to_create = fields.Selection(
        related="purchase_type_id.to_create",
    )
    procurement_method_ids = fields.Many2many(
        related="purchase_type_id.procurement_method_ids",
    )

    # -- Header info --
    title = fields.Char(string="Title", tracking=True)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        copy=False,
        default=lambda self: self.env.user,
        index=True,
    )
    assigned_to = fields.Many2one(
        string="Purchase Representative",
        copy=False,
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
    )
    payment_type = fields.Selection(
        [("direct", "Direct paid"), ("advance", "Advance"), ("prepaid", "Prepaid")],
        tracking=True,
    )
    expense_reason = fields.Text(
        string="Reason",
    )
    is_construction = fields.Boolean(string="Construction", readonly=True)

    # -- Workflow --
    verified_by = fields.Many2one(
        comodel_name="res.users",
        index=True,
        copy=False,
        tracking=True,
    )
    date_verified = fields.Date(
        string="Verified Date",
        copy=False,
    )
    approved_by = fields.Many2one(
        comodel_name="res.users",
        index=True,
        copy=False,
        tracking=True,
    )
    date_approved = fields.Date(
        string="Approved Date",
        copy=False,
    )
    hide_create_po_button = fields.Boolean(compute="_compute_hide_create_po_button")

    # -- Committees --
    procurement_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Procurement Committees",
        domain=[("committee_type", "=", "procurement")],
        copy=True,
    )
    work_acceptance_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Work Acceptance Committees",
        domain=[("committee_type", "=", "work_acceptance")],
        copy=True,
    )
    tor_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="TOR Committees",
        domain=[("committee_type", "=", "tor_committee")],
        copy=True,
    )
    price_determine_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Price Determine Committees",
        domain=[("committee_type", "=", "price_determine")],
        copy=True,
    )
    evaluation_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Evaluation Committees",
        domain=[("committee_type", "=", "evaluation")],
        copy=True,
    )
    work_supervisor_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Work Supervisors",
        domain=[("committee_type", "=", "work_supervisor")],
        copy=True,
    )

    # -- Attachments --
    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Document Attachments",
        tracking=True,
    )

    @api.depends("state", "purchase_count")
    def _compute_hide_create_po_button(self):
        for rec in self:
            rec.hide_create_po_button = not (
                rec.state in ("approved", "in_progress") and rec.purchase_count == 0
            )

    def _get_domain_purchase_type(self):
        return [("visible_on_purchase_request", "=", True)]

    def get_estimated_cost_currency(self, date=False):
        """Return estimated cost converted to company currency.

        If the optional module `purchase_request_manual_currency` is installed
        and a custom rate is set on the request, that rate is used instead of
        the standard currency conversion.
        """
        self.ensure_one()
        date = date or fields.Date.context_today(self)
        estimated_cost = sum(self.line_ids.mapped("estimated_cost"))
        if self.currency_id != self.company_id.currency_id:
            if hasattr(self, "manual_currency") and self.manual_currency:
                rate = (
                    self.custom_rate
                    if self.type_currency == "inverse_company_rate"
                    else (1.0 / self.custom_rate)
                )
                estimated_cost = estimated_cost * rate
            else:
                estimated_cost = self.currency_id._convert(
                    estimated_cost, self.company_id.currency_id, self.company_id, date
                )
        return estimated_cost

    @api.onchange("purchase_type_id")
    def _onchange_purchase_type_id(self):
        methods = self.purchase_type_id.procurement_method_ids
        self.procurement_method_id = methods if len(methods) == 1 else False

    def button_approved(self):
        self.write(
            {
                "approved_by": self.env.user.id,
                "date_approved": fields.Date.context_today(self),
            }
        )
        return super().button_approved()
