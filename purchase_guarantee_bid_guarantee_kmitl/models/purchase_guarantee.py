# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseGuarantee(models.Model):
    _inherit = 'purchase.guarantee'

    reference = fields.Reference(
        selection='_reference_selection',
    )

    request_id = fields.Many2one(
        comodel_name="purchase.request",
        compute="_compute_reference",
        string="Purchase Request",
        index=True,
        store=True,
        ondelete="restrict",
    )

    is_purchase_request = fields.Boolean(
        string="Is Purchase Request",
        compute="_compute_reference",
        store=True,
        help="True if reference is purchase.request"
    )

    @api.model
    def _reference_selection(self):
        return [
            ("purchase.request", "Purchase Request"),
            ("purchase.order", "Purchase Order"),
        ]

    @api.depends("reference")
    def _compute_reference(self):
        for rec in self.filtered("reference"):
            rec.request_id = False
            rec.is_purchase_request = False
            if rec.reference._name == "purchase.request":
                rec.request_id = rec.reference
                rec.reference_model = rec.reference._name
                rec.is_purchase_request = True
            elif rec.reference._name == "purchase.order":
                rec.purchase_id = rec.reference
                if rec.reference.state in ["draft", "sent"]:
                    rec.reference_model = "{}.{}".format(rec.reference._name, "rfq")
                elif rec.reference.state in ["purchase"]:
                    rec.reference_model = "{}.{}".format(rec.reference._name, "po")
            rec._check_reference_status()

    def _check_reference_status(self):
        self.ensure_one()
        if self.reference:
            states = []
            if self.reference._name == "purchase.request":
                states.extend(["approved", "in_progress"])
            elif self.reference._name == "purchase.order":
                states.extend(["draft", "sent", "purchase"])
            if states and self.reference.state not in states:
                raise UserError(
                    _("%(ref)s must be in status: %(state)s")
                    % {
                        "ref": dict(self._reference_selection()).get(
                            self.reference._name
                        ),
                        "state": ", ".join(
                            [
                                dict(self.reference._fields["state"].selection).get(
                                    state
                                )
                                for state in states
                            ]
                        ),
                    }
                )
    
    @api.depends("reference")
    def _compute_guarantee_method_id(self):
        GuaranteeMethod = self.env["purchase.guarantee.method"]
        for rec in self.filtered("reference"):
            dom = []
            if rec.reference._name == "purchase.request":
                dom = [("default_for_model", "=", rec.reference._name)]
            elif rec.reference._name == "purchase.order":
                if rec.reference.state in ["draft", "sent"]:
                    dom = [
                        (
                            "default_for_model",
                            "=",
                            "{}.{}".format(rec.reference._name, "rfq"),
                        )
                    ]
                elif rec.reference.state in ["purchase"]:
                    dom = [
                        (
                            "default_for_model",
                            "=",
                            "{}.{}".format(rec.reference._name, "po"),
                        )
                    ]
            rec.guarantee_method_id = GuaranteeMethod.search(dom)[:1]

    def action_view_purchase_request(self):
        self.ensure_one()
        if not self.request_id:
            return
            
        return {
            'name': _('Purchase Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request',
            'res_id': self.request_id.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': self.env.context,
        }