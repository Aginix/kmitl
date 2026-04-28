from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    _STATES = [
        ("waiting", "Waiting for e-GP"),
        ("in_progress", "In progress e-GP"),
        ("done", "done e-GP")
    ]

    is_egp = fields.Boolean(
        string="e-GP",
        compute="_compute_is_egp",
        store=True,
    )
    egp_project_id = fields.Char(string="เลขที่โครงการ e-GP", tracking=True)
    egp_project_url = fields.Char(
        string="ลิงค์ e-GP", compute="_compute_egp_project_url", readonly=True
    )
    egp_status = fields.Selection(
        selection=_STATES,
        string="e-GP Status",
        tracking=True,
        copy=False,
    )
    can_edit_egp = fields.Boolean(
        compute="_compute_can_edit_egp",
        default=False,
    )
    show_egp_create_purchase_order_button = fields.Boolean(compute="_show_egp_create_purchase_order_button")

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

    def _show_egp_create_purchase_order_button(self):
        for rec in self:
            rec.show_egp_create_purchase_order_button = False
            if rec.is_egp and rec.state in ('approved', 'in_progress') and rec.purchase_count == 0:
                rec.show_egp_create_purchase_order_button = True

    @api.depends_context("uid")
    def _compute_can_edit_egp(self):
        user_in_group = self.env.user.has_group(
            "purchase_request_kmitl.group_purchase_request_user_all"
        )
        for record in self:
            record.can_edit_egp = bool(user_in_group and record.egp_status == "waiting")

    def _hide_create_po_button(self):
        super()._hide_create_po_button()
        for rec in self:
            if rec.is_egp:
                rec.hide_create_po_button = True

    def action_egp_create_purchase_order(self):
        for record in self:
            if record.is_egp and record.egp_status not in ['in_progress']:
                raise UserError("ท่านสามารถสร้างใบสั่งซื้อ/จ้างได้เมื่ออยู่ในกระบวนการ e-GP เท่านั้น")

        action = self.env.ref("purchase_request.action_purchase_request_line_make_purchase_order").sudo().read()[0]
        return action

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if 'state' in vals and record.is_egp:
                if record.state == "approved":
                    record.egp_status = "waiting"
        return res

    def action_del_egp_status(self):
        for record in self:
            if record.is_egp:
                record.egp_status = False

    # check if have egp_project_id
    def action_egp_in_progress(self):
        for record in self:
            if record.is_egp:
                if not record.egp_project_id:
                    raise UserError(_("กรุณากรอกเลขที่โครงการ e-GP ก่อนดำเนินการ"))
                record.egp_status = "in_progress"

    def button_draft(self):
        res = super().button_draft()
        self.write({"egp_status": False})
        return res

    def button_rejected_egp(self):
        self.action_del_egp_status()
        return self.button_rejected()