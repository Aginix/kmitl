from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import float_compare


class InstallmentWizardLine(models.TransientModel):
    _name = "purchase.order.change.installment.wizard.line"
    _description = "Installment Change Wizard Line"
    _order = "installment"

    wizard_id = fields.Many2one(
        comodel_name="purchase.order.change.wizard",
        ondelete="cascade",
    )
    installment_id = fields.Many2one(
        comodel_name="purchase.invoice.plan",
        string="งวดงาน",
    )
    installment = fields.Integer(string="งวดที่", readonly=True)
    has_wa = fields.Boolean(string="มี WA แล้ว")
    wa_id = fields.Many2one(
        comodel_name="work.acceptance",
        string="อ้างอิงใบตรวจรับ",
        readonly=True,
    )
    wa_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_review", "In Review"),
            ("accept", "Accepted"),
            ("cancel", "Cancelled"),
        ],
        string="สถานะใบตรวจรับ",
        readonly=True,
    )
    plan_date = fields.Date(string="วันที่กำหนด")
    duration_days = fields.Integer(string="ระยะเวลา (วัน)")
    percent = fields.Float(string="ร้อยละ")
    amount = fields.Monetary(string="จำนวนเงิน", readonly=True)
    deliverables = fields.Text(string="สิ่งของที่ต้องส่งมอบ")
    po_amount_total = fields.Monetary(string="ยอดรวม")
    po_work_start = fields.Date(string="วันที่เริ่มงาน")
    currency_id = fields.Many2one(
        related="wizard_id.purchase_id.currency_id",
        readonly=True,
    )

    @api.onchange("percent")
    def _onchange_percent(self):
        if self.po_amount_total:
            self.amount = self.percent * self.po_amount_total / 100

    @api.onchange("duration_days")
    def _onchange_duration_days(self):
        if self.duration_days and self.po_work_start:
            self.plan_date = self.po_work_start + timedelta(days=self.duration_days)


class PurchaseOrderChangeWizard(models.TransientModel):
    _inherit = "purchase.order.change.wizard"

    show_installment = fields.Boolean()
    installment_line_ids = fields.One2many(
        comodel_name="purchase.order.change.installment.wizard.line",
        inverse_name="wizard_id",
        string="งวดงาน",
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)

        default_section_ids = self.env.context.get("default_section_ids")
        if default_section_ids and isinstance(default_section_ids, list):
            ids = default_section_ids[0][2]
        else:
            ids = []

        sections = self.env["purchase.change.section"].browse(ids)
        xml_ids_map = sections.get_external_id()
        xml_id_list = [xml.split(".")[-1] for xml in xml_ids_map.values()]

        vals["show_installment"] = (
            "purchase_change_section_installment" in xml_id_list
        )

        purchase = self.env["purchase.order"].browse(
            self.env.context.get("default_purchase_id")
        )
        if purchase:
            vals["installment_line_ids"] = [
                (0, 0, {
                    "installment_id": plan.id,
                    "installment": plan.installment,
                    "plan_date": plan.plan_date,
                    "duration_days": plan.duration_days,
                    "percent": plan.percent,
                    "amount": plan.amount,
                    "deliverables": plan.deliverables,
                    "has_wa": bool(plan.wa_id),
                    "wa_id": plan.wa_id.id,
                    "wa_state": plan.wa_state or False,
                    "po_amount_total": purchase.amount_total,
                    "po_work_start": purchase.work_start,
                })
                for plan in purchase.invoice_plan_ids
            ]
        return vals

    def action_save_changes(self):
        if self.show_installment:
            self._save_installment_change()
        return super().action_save_changes()

    def _save_installment_change(self):
        self.ensure_one()
        Snapshot = self.env["purchase.order.change.installment.snapshot"].sudo()

        for line in self.installment_line_ids:
            plan = line.installment_id
            if not plan or line.has_wa:
                continue

            changed = (
                plan.plan_date != line.plan_date
                or plan.duration_days != line.duration_days
                or float_compare(plan.percent, line.percent, precision_digits=2)
                != 0
                or (plan.deliverables or "") != (line.deliverables or "")
            )
            if not changed:
                continue

            Snapshot.create({
                "change_id": self.change_id.id,
                "snapshot_type": "before",
                "installment_id": plan.id,
                "installment": plan.installment,
                "plan_date": plan.plan_date,
                "duration_days": plan.duration_days,
                "percent": plan.percent,
                "amount": plan.amount,
                "deliverables": plan.deliverables,
            })
            Snapshot.create({
                "change_id": self.change_id.id,
                "snapshot_type": "after",
                "installment_id": plan.id,
                "installment": plan.installment,
                "plan_date": line.plan_date,
                "duration_days": line.duration_days,
                "percent": line.percent,
                "amount": line.amount,
                "deliverables": line.deliverables,
            })

            plan.sudo().write({
                "plan_date": line.plan_date,
                "duration_days": line.duration_days,
                "percent": line.percent,
                "deliverables": line.deliverables,
            })
