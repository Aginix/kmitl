from odoo import api, fields, models


class PurchaseOrderChangeWizard(models.TransientModel):
    _inherit = "purchase.order.change.wizard"

    show_installment = fields.Boolean()
    editable_installment_ids = fields.Many2many(
        comodel_name="purchase.invoice.plan",
    )
    installment_id = fields.Many2one(
        comodel_name="purchase.invoice.plan",
        string="งวดงานที่ต้องการแก้ไข",
        domain="[('id', 'in', editable_installment_ids)]",
    )
    # ค่าเดิม (readonly)
    plan_date_old = fields.Date(string="กำหนดวันส่ง (เดิม)", readonly=True)
    duration_days_old = fields.Integer(string="จำนวนวัน (เดิม)", readonly=True)
    percent_old = fields.Float(string="สัดส่วน % (เดิม)", readonly=True)
    amount_old = fields.Monetary(string="จำนวนเงิน (เดิม)", readonly=True)
    deliverables_old = fields.Text(string="รายละเอียดงาน (เดิม)", readonly=True)
    # ค่าใหม่
    plan_date = fields.Date(string="กำหนดวันส่ง (ใหม่)")
    duration_days = fields.Integer(string="จำนวนวัน (ใหม่)")
    percent = fields.Float(string="สัดส่วน % (ใหม่)")
    amount = fields.Monetary(string="จำนวนเงิน (ใหม่)", readonly=True)
    deliverables = fields.Text(string="รายละเอียดงาน (ใหม่)")

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
            plans = purchase.invoice_plan_ids.filtered(
                lambda p: p.wa_state not in ("in_review", "accept")
            )
            vals["editable_installment_ids"] = [(6, 0, plans.ids)]
        return vals

    @api.onchange("installment_id")
    def _onchange_installment_id(self):
        plan = self.installment_id
        self.plan_date_old = plan.plan_date
        self.duration_days_old = plan.duration_days
        self.percent_old = plan.percent
        self.amount_old = plan.amount
        self.deliverables_old = plan.deliverables
        self.plan_date = plan.plan_date
        self.duration_days = plan.duration_days
        self.percent = plan.percent
        self.amount = plan.amount
        self.deliverables = plan.deliverables

    @api.onchange("percent")
    def _onchange_percent(self):
        amount_total = self.purchase_id.amount_total
        if amount_total:
            self.amount = self.percent * amount_total / 100

    def action_save_changes(self):
        if self.show_installment:
            self._save_installment_change()
        return super().action_save_changes()

    def _save_installment_change(self):
        self.ensure_one()
        plan = self.installment_id
        if not plan:
            return

        Snapshot = self.env["purchase.order.change.installment.snapshot"].sudo()
        Snapshot.create({
            "change_id": self.change_id.id,
            "snapshot_type": "before",
            "installment_id": plan.id,
            "installment": plan.installment,
            "plan_date": self.plan_date_old,
            "duration_days": self.duration_days_old,
            "percent": self.percent_old,
            "amount": self.amount_old,
            "deliverables": self.deliverables_old,
        })
        Snapshot.create({
            "change_id": self.change_id.id,
            "snapshot_type": "after",
            "installment_id": plan.id,
            "installment": plan.installment,
            "plan_date": self.plan_date,
            "duration_days": self.duration_days,
            "percent": self.percent,
            "amount": self.amount,
            "deliverables": self.deliverables,
        })

        plan.sudo().write({
            "plan_date": self.plan_date,
            "duration_days": self.duration_days,
            "percent": self.percent,
            "deliverables": self.deliverables,
        })
