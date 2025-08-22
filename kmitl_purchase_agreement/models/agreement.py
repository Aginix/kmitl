# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class Agreement(models.Model):
    _inherit = 'agreement'

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    project_ids = fields.Selection(
        [("project_1", "Project 1"), ("project_2", "Project 2")],
        string="Project",
    )

    document_ids = fields.One2many(
        comodel_name="purchase.order.attachment",
        inverse_name="request_id",
        string="Attachment",
        related="purchase_order_id.document_ids",
        readonly=True,
    )

    reversion_document_ids = fields.One2many(
        comodel_name="purchase.agreement.attachment",
        inverse_name="request_id",
        string="Attachment",
    )

    verify_datetime = fields.Date(string="Date of Verification")
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string="PO Ref",
        ondelete="set null",
    )

    pr1_total = fields.Monetary(related='purchase_order_id.pr1_total', string='PR1 Total')

    invoice_plan_ids = fields.One2many(
        comodel_name="purchase.invoice.plan",
        inverse_name="purchase_id",
        string="Invoice Plan",
        related="purchase_order_id.invoice_plan_ids",
        readonly=True,
    )

    work_acceptance_committee_ids = fields.One2many(
        related='purchase_order_id.work_acceptance_committee_ids',
        readonly=True,
    )
    tor_committee_ids = fields.One2many(
        related='purchase_order_id.tor_committee_ids',
        readonly=True,
    )
    price_determine_committee_ids = fields.One2many(
        related='purchase_order_id.price_determine_committee_ids',
        readonly=True,
    )
    evaluation_committee_ids = fields.One2many(
        related='purchase_order_id.evaluation_committee_ids',
        readonly=True,
    )

    fee = fields.Char(
        related='purchase_order_id.fee',
        string='Fee Per Day',
    )

    contract_type = fields.Selection(
        related='purchase_order_id.contract_type',
        string="Contract type",
        store=True,
        readonly=False
    )

    work_start_date = fields.Date(related='purchase_order_id.work_start_date', string="Work start date")
    work_end_date = fields.Date(related='purchase_order_id.work_end_date', string="Work end date")

    is_invoice = fields.Boolean(
        related='purchase_order_id.use_invoice_plan',
        store=True
    )

    def action_open_new_version_wizard(self):
        self.ensure_one()
        return {
            "name": "Create New Version",
            "type": "ir.actions.act_window",
            "res_model": "agreement.new.version.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_agreement_id": self.id,
            },
        }

    def create_new_version(self):
        for rec in self:
            if not rec.state == "draft":
                rec.state = "draft"
            rec.copy(default=rec._get_old_version_default_vals())
            rec.update({"version": rec.version + 1})
        return super().write({"revision": 0})

    def _exclude_readonly_field(self):
        return [
            "stage_id",
            "contract_type",
            "work_start_date",
            "work_end_date",
        ]
