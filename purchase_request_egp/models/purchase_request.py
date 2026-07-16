from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    is_egp = fields.Boolean(
        string="e-GP",
        compute="_compute_is_egp",
        store=True,
    )
    egp_project_id = fields.Char(string="เลขที่โครงการ e-GP", tracking=True)
    egp_project_url = fields.Char(
        string="ลิงค์ e-GP", compute="_compute_egp_project_url", readonly=True
    )
    can_edit_egp = fields.Boolean(
        compute="_compute_can_edit_egp",
        default=False,
    )
    show_egp_create_purchase_order_button = fields.Boolean(
        compute="_show_egp_create_purchase_order_button"
    )

    @api.depends("egp_project_id")
    def _compute_egp_project_url(self):
        for record in self:
            record.egp_project_url = record.get_epg_project_url()

    def get_epg_project_url(self):
        if not self.egp_project_id:
            return False
        ts = str(datetime.now().timestamp())
        project_id = self.egp_project_id
        return f"https://process.gprocurement.go.th/egp2procmainWeb/jsp/public_announ_search.jsp?projectId={project_id}&homeflag=QR"

    @api.depends('estimated_cost')
    def _compute_is_egp(self):
        for rec in self:
            if rec.estimated_cost and rec.estimated_cost > 100000:
                rec.is_egp = True
            else:
                rec.is_egp = rec.is_egp

    @api.depends("state", "is_egp", "purchase_count")
    def _show_egp_create_purchase_order_button(self):
        for rec in self:
            rec.show_egp_create_purchase_order_button = (
                rec.is_egp and rec.state == "purchasing" and rec.purchase_count == 0
            )

    @api.depends_context("uid")
    def _compute_can_edit_egp(self):
        user_in_group = self.env.user.has_group(
            "purchase_request_kmitl.group_purchase_request_user_all"
        )
        for record in self:
            # egp_project_id is editable only while in egp state
            record.can_edit_egp = bool(user_in_group and record.state == "egp")

    def _hide_create_po_button(self):
        """egp PRs cannot create PO directly — must go through egp → purchasing flow."""
        super()._hide_create_po_button()
        for rec in self:
            if rec.is_egp and rec.state != "purchasing":
                rec.hide_create_po_button = True

    def action_egp_create_purchase_order(self):
        for record in self:
            if record.is_egp and record.state != "purchasing":
                raise UserError(
                    "ท่านสามารถสร้างใบสั่งซื้อ/จ้างได้เมื่ออยู่ในสถานะ 'อยู่ระหว่างจัดซื้อจัดจ้าง' เท่านั้น"
                )
        action = (
            self.env.ref("purchase_request.action_purchase_request_line_make_purchase_order")
            .sudo()
            .read()[0]
        )
        return action

    def action_egp_in_progress(self):
        """egp → purchasing: validate egp_project_id then advance state."""
        for record in self:
            if record.is_egp:
                if not record.egp_project_id:
                    raise UserError(_("กรุณากรอกเลขที่โครงการ e-GP ก่อนดำเนินการ"))
                record.write({"state": "purchasing"})
