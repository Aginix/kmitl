# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    _STATES = [
    ("draft", "Draft"),
    ("submit", "Submit"),
    ("approved", "Approved"),
    ("accept", "Accepted"),
    ("cancel", "Cancelled"),
    ]

    agreement_id = fields.Many2one(
        "agreement", 
        string="Agreement Ref"
    )

    agreement_version = fields.Integer(
        related='agreement_id.version'
    )

    document_ids = fields.One2many(
        "purchase.work.acceptance.attachment",
        "wa_id",
        string="Attachment",
    )

    work_acceptance_committee_ids = fields.One2many(
        related='agreement_id.work_acceptance_committee_ids',
        readonly=True,
    )
    state = fields.Selection(
        selection=_STATES,
        string="Status",
        readonly=True,
        index=True,
        copy=False,
        default="draft",
        tracking=True,
    )
    is_editable = fields.Boolean(compute="_compute_is_editable", readonly=True)
    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in (
                "submit",
                "approved",
                "accept",
                "cancel",
            ):
                rec.is_editable = False
            else:
                rec.is_editable = True

    def button_submit(self):
        self.write({"state": "submit"})

    def button_approved(self):
        self.write({"state": "approved"})

    def button_draft(self):
        picking_obj = self.env["stock.picking"]
        wa_ids = picking_obj.search([("wa_id", "in", self.ids)])
        if wa_ids:
            raise UserError(
                _(
                    "Unable to set to draft this work acceptance. "
                    "You must first cancel the related receipts."
                )
            )

        for rec in self:
            if rec.document_ids:
                rec.document_ids.unlink()

        self.write({"state": "draft"})