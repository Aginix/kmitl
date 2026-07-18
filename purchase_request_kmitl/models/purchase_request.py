from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    state = fields.Selection(
        selection_add=[
            ("to_submit", "To Submit"),
            ("to_approve",),
            ("cancel", "Cancel"),
        ],
        ondelete={"to_submit": "set default", "cancel": "set default"},
    )

    procurement_type_id = fields.Many2one(
        comodel_name="procurement.type",
        string="Procurement Type",
        ondelete="restrict",
        index=True,
    )
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        ondelete="restrict",
        index=True,
    )
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
    payment_type = fields.Selection(
        [("direct", "Direct paid"), ("advance", "Advance"), ("prepaid", "Prepaid")],
        tracking=True,
    )
    assigned_to = fields.Many2one(
        string="Purchase Representative",
        copy=False,
    )
    verified_by = fields.Many2one(
        comodel_name="res.users",
        index=True,
        copy=False,
        tracking=True,
    )
    approved_by = fields.Many2one(
        comodel_name="res.users",
        index=True,
        copy=False,
        tracking=True,
    )
    date_verified = fields.Date(
        string="Verified Date",
        copy=False,
    )
    date_approved = fields.Date(
        string="Approved Date",
        copy=False,
    )
    is_construction = fields.Boolean(string="Construction", readonly=True)
    title = fields.Char(string="Title", tracking=True)
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
    )
    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Document Attachments",
        tracking=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        copy=False,
        default=lambda self: self.env.user,
        index=True,
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
    hide_create_po_button = fields.Boolean(compute="_hide_create_po_button")

    @api.depends("state")
    def _hide_create_po_button(self):
        for rec in self:
            rec.hide_create_po_button = not (
                rec.state in ("approved", "in_progress")
                and rec.purchase_count == 0
            )

    def get_estimated_cost_currency(self, date=False):
        """Return the total estimated cost across all lines."""
        self.ensure_one()
        return sum(self.line_ids.mapped("estimated_cost"))

    def _apply_sarabun_approve_metadata(self):
        self.write(
            {
                "approved_by": self.env.user.id,
                "date_approved": fields.Date.context_today(self),
            }
        )

    def _transition_after_sarabun_approve(self):
        """Dispatch state transition after Sarabun completes routing.

        Overridden in purchase_request_egp (is_egp=True → in_egp) and
        purchase_request_approval (is_egp=False → in_approval + auto-PA).
        The base fallback writes 'approved' if neither branch is installed.
        """
        self._apply_sarabun_approve_metadata()
        self.write({"state": "approved"})

    def button_approved(self):
        self._apply_sarabun_approve_metadata()
        return super().button_approved()

    def button_to_submit(self):
        return self.write({"state": "to_submit"})

    def button_cancel(self):
        return self.write({"state": "cancel"})
