# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    purchase_request_approval_id = fields.Many2one(
        comodel_name="purchase.request.approval",
        string="Purchase Request Approval",
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        ondelete="set null",
    )

    def _get_source_document(self):
        return self.purchase_request_approval_id or super()._get_source_document()

    def _get_return_source(self):
        """A PRA-linked DR returns to its purchase request approval for
        correction."""
        return self.purchase_request_approval_id or super()._get_return_source()

    def action_view_purchase_approval(self):
        self.ensure_one()
        if not self.purchase_request_approval_id:
            raise UserError(
                _("No Purchase Request Approval linked to this request.")
            )

        return {
            "type": "ir.actions.act_window",
            "name": _("Purchase Request Approval"),
            "res_model": "purchase.request.approval",
            "res_id": self.purchase_request_approval_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def _message_link_back_to_request(self):
        pa = self.purchase_request_approval_id
        body = _(
            'Created from Purchase Request Approval'
            ' <a href="%(link)s" target="_blank">%(name)s</a>.',
            link=pa._get_record_url(),
            name=pa.name,
        )
        pr = pa.request_id
        if pr:
            body += "<ul><li>%s</li></ul>" % (
                _('Purchase Request: <a href="%(link)s" target="_blank">%(name)s</a>')
                % {"link": pr._get_record_url(), "name": pr.name}
            )
        return body
