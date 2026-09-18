# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    contract_ids = fields.One2many(
        "purchase.contract",
        "purchase_id",
        string="Contract Revisions",
        copy=False,
    )
    current_contract_id = fields.Many2one(
        "purchase.contract",
        string="Current Contract",
        compute="_compute_current_contract",
        store=True,
    )
    revision_count = fields.Integer(
        string="Revision Count",
        compute="_compute_revision_count",
    )

    @api.depends("contract_ids.state", "contract_ids.revision_number")
    def _compute_current_contract(self):
        for po in self:
            applied = po.contract_ids.filtered(lambda r: r.state == "applied")
            po.current_contract_id = (
                applied.sorted("revision_number", reverse=True)[:1].id or False
            )

    @api.depends("contract_ids")
    def _compute_revision_count(self):
        for po in self:
            po.revision_count = len(po.contract_ids)

    # ------------------------------------------------------------------
    # Rev 0 hook
    # ------------------------------------------------------------------
    def button_confirm(self):
        res = super().button_confirm()
        for po in self:
            if not po.contract_ids:
                po._create_original_contract()
        return res

    def _create_original_contract(self):
        """Snapshot the PO as rev 0 immediately after confirm."""
        self.ensure_one()
        contract = self.env["purchase.contract"].create(
            {
                "purchase_id": self.id,
                "revision_number": 0,
                "state": "applied",
                "fines_rate": self.fines_rate,
                "supervision_cost": self.supervision_cost,
                "date_order_date": self.date_order_date,
                "work_start": self.work_start,
                "extension_days": 0,
                "applied_by": self.env.uid,
                "applied_date": fields.Datetime.now(),
            }
        )
        contract._snapshot_lines_from_po(self)
        contract._snapshot_invoice_plan_from_po(self)
        contract._snapshot_committees_from_po(self)
        return contract

    # ------------------------------------------------------------------
    # Rev N entry point
    # ------------------------------------------------------------------
    def action_open_contract_revision(self):
        """Open (or create) the current draft amendment for this PO."""
        self.ensure_one()
        if not self.current_contract_id:
            raise UserError(
                _("PO นี้ยังไม่มีสัญญาต้นฉบับ — กด 'ยืนยัน' ที่ PO ก่อน")
            )
        draft = self.contract_ids.filtered(lambda r: r.state == "draft")
        if len(draft) > 1:
            raise UserError(
                _("PO นี้มี revision draft ค้างอยู่มากกว่า 1 ใบ กรุณาติดต่อผู้ดูแลระบบ")
            )
        if not draft:
            latest = self.current_contract_id
            draft = self.env["purchase.contract"].create(
                {
                    "purchase_id": self.id,
                    "revision_number": latest.revision_number + 1,
                    "state": "draft",
                    "fines_rate": latest.fines_rate,
                    "supervision_cost": latest.supervision_cost,
                    "date_order_date": latest.date_order_date,
                    "work_start": latest.work_start,
                    # extension_days starts at 0 — this rev's delta only
                }
            )
            draft._clone_lines_from(latest)
            draft._clone_invoice_plan_from(latest)
            draft._clone_committees_from(latest)
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.contract",
            "res_id": draft.id,
            "view_mode": "form",
            "target": "current",
        }
