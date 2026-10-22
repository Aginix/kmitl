# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

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
        compute_sudo=False
    )

    is_purchase_request = fields.Boolean(
        string="Is Purchase Request",
        compute="_compute_reference",
        store=False,
        help="True if reference is purchase.request",
        compute_sudo=False
    )

    @api.model
    def _reference_selection(self):
        return [
            ("purchase.request", "Purchase Request"),
            ("purchase.order", "Purchase Order"),
        ]

    @api.depends("reference")
    def _compute_reference(self):
        res = super()._compute_reference()
        for rec in self:
            rec.request_id = False
            rec.is_purchase_request = False

            if rec.reference:
                if rec.reference._name == "purchase.request":
                    rec.request_id = rec.reference
                    rec.reference_model = rec.reference._name
                    rec.is_purchase_request = True
                rec._check_reference_status()
        return res

    def _check_reference_status(self):
        super()._check_reference_status()
        if self.reference:
            states = []
            if self.reference._name == "purchase.request":
                states.extend(["approved", "in_progress", "done"])
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
        super()._compute_guarantee_method_id()
        for rec in self.filtered("reference"):
            if rec.reference._name == "purchase.request":
                dom = [("default_for_model", "=", rec.reference._name)]
                rec.guarantee_method_id = self.env["purchase.guarantee.method"].search(dom)[:1]

    @api.depends("reference")
    def _compute_analytic(self):
        super()._compute_analytic()
        for rec in self.filtered("reference"):
            if rec.reference._name == "purchase.request":
                merged = {}
                origin = rec.reference.line_ids
                if "analytic_distribution" in origin._fields:
                    for line in origin:
                        if line.analytic_distribution:
                            merged.update(line.analytic_distribution)
                rec.analytic_distribution = merged or False

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