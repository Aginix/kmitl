# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseGuarantee(models.Model):
    _inherit = 'purchase.guarantee'

    reference = fields.Reference(
        selection=[
            ("purchase.request", "Purchase Request"),
            ("purchase.order", "Purchase Order"),
        ],
    )

    request_id = fields.Many2one(
        comodel_name="purchase.request",
        compute="_compute_reference",
        string="Purchase Request",
        index=True,
        store=True,
        ondelete="restrict",
    )

    @api.depends("reference")
    def _compute_reference(self):
        for rec in self.filtered("reference"):
            # if rec.reference._name == "purchase.requisition":
            #     rec.requisition_id = rec.reference
            #     rec.reference_model = rec.reference._name
            if rec.reference._name == "purchase.request":
                rec.request_id = rec.reference
                rec.reference_model = rec.reference._name
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
            # if self.reference._name == "purchase.requisition":
            #     states.extend(["in_progress", "open"])
            if self.reference._name == "purchase.request":
                states.extend(["approved"])
            elif self.reference._name == "purchase.order":
                states.extend(["draft", "sent", "purchase"])
            if states and self.reference.state not in states:
                raise UserError(
                    _("%(ref)s must be in status: %(state)s")
                    % {
                        "ref": dict(self._fields["reference"].selection).get(
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
            # if rec.reference._name == "purchase.requisition":
            #     dom = [("default_for_model", "=", rec.reference._name)]
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