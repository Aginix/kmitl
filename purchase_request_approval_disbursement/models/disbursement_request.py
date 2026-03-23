# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    reference = fields.Reference(
        selection_add=[("purchase.request.approval", "Purchase Request Approval")],
        ondelete={"purchase.request.approval": "set null"},
    )

    purchase_request_approval_id = fields.Many2one(
        comodel_name="purchase.request.approval",
        string="Purchase Request Approval",
        compute="_compute_reference_fields",
        store=True,
        index=True,
        tracking=True,
    )

    @api.depends("reference")
    def _compute_reference_fields(self):
        super()._compute_reference_fields()
        for rec in self:
            if rec.reference and rec.reference._name == "purchase.request.approval":
                rec.purchase_request_approval_id = rec.reference
            else:
                rec.purchase_request_approval_id = False

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
            pr_link = "/web#id=%d&model=purchase.request&view_type=form" % pr.id
            body += "<ul><li>%s</li></ul>" % (
                _('Purchase Request: <a href="%(link)s" target="_blank">%(name)s</a>')
                % {"link": pr_link, "name": pr.name}
            )
        return body
