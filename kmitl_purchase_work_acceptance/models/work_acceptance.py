# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    agreement_id = fields.Many2one("agreement", string="Agreement Ref")

    document_ids = fields.One2many(
        "purchase.work.acceptance.attachment",
        "request_id",
        string="Attachment",
    )

    # filler
    invoice_plan = fields.Char(string='Invocie plan')

    work_acceptance_committee_ids = fields.One2many(
        related='agreement_id.work_acceptance_committee_ids',
        readonly=True,
    )

    state = fields.Selection(
        [("draft", "Draft"), ("submit", "Submit"), ("approved", "Approved"), ("accept", "Accepted"), ("cancel", "Cancelled")],
        string="Status",
        readonly=True,
        index=True,
        copy=False,
        default="draft",
        tracking=True,
    )

    def button_submit(self):
        self.write({"state": "submit"})

    def button_approved(self):
        self.write({"state": "approved"})