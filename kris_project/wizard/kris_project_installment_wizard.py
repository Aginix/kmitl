from odoo import _, api, fields, models
from odoo.exceptions import UserError


class KrisProjectInstallmentWizard(models.TransientModel):
    _name = "kris.project.installment.wizard"
    _description = "KRIS Project Installment Wizard"

    project_id = fields.Many2one(
        comodel_name="kris.project",
        string="โครงการ",
        required=True,
        readonly=True,
    )
    name = fields.Char(string="งวดที่", required=True)
    amount = fields.Monetary(string="จำนวนเงิน")
    due_date = fields.Date(string="วันครบกำหนด")
    allocation_ids = fields.One2many(
        comodel_name="kris.project.installment.wizard.line",
        inverse_name="wizard_id",
        string="การจัดสรร",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="project_id.currency_id",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        project_id = res.get("project_id") or self.env.context.get("default_project_id")
        if project_id and "allocation_ids" in fields_list:
            project = self.env["kris.project"].browse(project_id)
            res["allocation_ids"] = [
                (0, 0, {"allocation_line_id": line.id, "amount": 0.0})
                for line in project.allocation_line_ids
            ]
        return res

    def action_save(self):
        self.ensure_one()
        project = self.project_id
        max_seq = max(project.installment_ids.mapped("sequence") or [0])
        installment = self.env["kris.project.installment"].create(
            {
                "project_id": project.id,
                "name": self.name,
                "amount": self.amount,
                "due_date": self.due_date,
                "sequence": max_seq + 10,
            }
        )
        for line in self.allocation_ids:
            self.env["kris.project.installment.allocation"].create(
                {
                    "installment_id": installment.id,
                    "allocation_line_id": line.allocation_line_id.id,
                    "amount": line.amount,
                }
            )
        return {"type": "ir.actions.act_window_close"}


class KrisProjectInstallmentWizardLine(models.TransientModel):
    _name = "kris.project.installment.wizard.line"
    _description = "KRIS Project Installment Wizard Line"
    _order = "allocation_line_id"

    wizard_id = fields.Many2one(
        comodel_name="kris.project.installment.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    allocation_line_id = fields.Many2one(
        comodel_name="kris.project.allocation.line",
        string="การจัดสรร",
        required=True,
    )
    name = fields.Char(
        related="allocation_line_id.name",
        string="ผู้รับจัดสรร",
        readonly=True,
    )
    estimated_amount = fields.Monetary(
        related="allocation_line_id.estimated_amount",
        string="ประมาณการ (บาท)",
        readonly=True,
    )
    allocated_amount = fields.Monetary(
        string="จัดสรรแล้ว",
        compute="_compute_allocated_amount",
        readonly=True,
    )
    remaining_amount = fields.Monetary(
        string="ยอดคงเหลือที่จัดสรรได้",
        compute="_compute_allocated_amount",
        readonly=True,
    )
    amount = fields.Monetary(string="จำนวนเงิน")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="wizard_id.currency_id",
        readonly=True,
    )

    @api.depends("allocation_line_id", "estimated_amount")
    def _compute_allocated_amount(self):
        InstAlloc = self.env["kris.project.installment.allocation"]
        for line in self:
            if not line.allocation_line_id:
                line.allocated_amount = 0.0
                line.remaining_amount = 0.0
                continue
            allocated = sum(
                InstAlloc.search(
                    [("allocation_line_id", "=", line.allocation_line_id.id)]
                ).mapped("amount")
            )
            line.allocated_amount = allocated
            line.remaining_amount = line.estimated_amount - allocated
