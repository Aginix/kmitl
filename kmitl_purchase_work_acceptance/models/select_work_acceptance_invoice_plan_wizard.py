# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SelectWorkAcceptanceInvoicePlanWizard(models.TransientModel):
    _inherit = 'select.work.acceptance.invoice.plan.wizard'

    agreement_id = fields.Many2one(
        comodel_name="agreement",
    )

    @api.depends("installment_id")
    def _compute_active_installment_ids(self):
        self.ensure_one()
        purchase = self.env["purchase.order"].browse(
            self.order_id.id
        )
        installment_ids = (
            purchase.wa_ids.filtered(lambda l: l.state != "cancel")
            .mapped("installment_id")
            .ids
        )
        self.active_installment_ids = self.env["purchase.invoice.plan"].search(
            [
                ("purchase_id", "=", purchase.id),
                ("id", "not in", installment_ids),
                ("installment", ">", 0),
            ]
        )

    def button_create_wa(self):
        purchase = self.env["purchase.order"].browse(self.env.context.get("active_id"))
        if self.installment_id not in self.active_installment_ids:
            raise UserError(
                _("Installment {} is already used by other WA.").format(
                    self.installment_id.installment
                )
            )
        res = purchase.with_context(
            installment_id=self.installment_id.id,
            wa_qty_line_ids=self.wa_qty_line_ids.ids,
        ).action_view_wa()
        res["context"]["default_installment_id"] = self.installment_id.id
        res["context"]["default_agreement_id"] = self.agreement_id.id
        return res