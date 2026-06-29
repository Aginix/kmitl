from odoo import api, fields, models


class KrisProjectReceiptWizard(models.TransientModel):
    _name = "kris.project.receipt.wizard"
    _description = "KRIS Project Receipt Wizard"

    project_id = fields.Many2one(
        comodel_name="kris.project",
        string="Project",
        required=True,
        readonly=True,
    )
    installment_id = fields.Many2one(
        comodel_name="kris.project.installment",
        string="Installment Number",
        domain="[('project_id', '=', project_id)]",
        ondelete="set null",
    )
    name = fields.Char(
        string="Receipt Number",
        required=True,
    )
    date = fields.Date(
        string="Receipt Date",
        required=True,
        default=fields.Date.context_today,
    )
    equipment_cost_in_installment = fields.Monetary(
        string="Equipment Cost in Installment",
        default=0.0,
    )
    amount = fields.Monetary(
        string="Amount",
    )
    net_amount = fields.Monetary(
        string="Net Amount",
        compute="_compute_net_amount",
    )
    extra_income = fields.Monetary(
        string="Extra Value",
    )
    allocation_ids = fields.One2many(
        comodel_name="kris.project.receipt.wizard.line",
        inverse_name="wizard_id",
        string="Allocation",
    )
    wizard_attachment_ids = fields.One2many(
        comodel_name="kris.project.receipt.wizard.attachment",
        inverse_name="wizard_id",
        string="Attachments",
    )
    note = fields.Text(
        string="Note",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="project_id.currency_id",
        string="สกุลเงิน",
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

    @api.depends("amount", "equipment_cost_in_installment")
    def _compute_net_amount(self):
        for wiz in self:
            wiz.net_amount = wiz.amount - wiz.equipment_cost_in_installment

    @api.onchange("installment_id")
    def _onchange_installment_id(self):
        inst = self.installment_id
        if not inst:
            return
        # A single installment (งวดงาน) may be recorded across several receipts,
        # so pre-fill only the amount still outstanding on it. Pre-filling the
        # full figures would double-count and trip the allocation / extra-income
        # guards; a fully-received installment therefore pre-fills zero, leaving
        # any over-collection to be entered deliberately.
        self.amount = max(0.0, inst.amount - inst.received_total)
        received_extra = sum(inst.receipt_ids.mapped("extra_income"))
        self.extra_income = max(0.0, inst.extra_income - received_extra)
        inst_alloc_by_line = {
            ia.allocation_line_id.id: ia.amount for ia in inst.allocation_ids
        }
        received_by_line = {}
        for receipt in inst.receipt_ids:
            for ra in receipt.allocation_ids:
                received_by_line[ra.allocation_line_id.id] = (
                    received_by_line.get(ra.allocation_line_id.id, 0.0) + ra.amount
                )
        for line in self.allocation_ids:
            lid = line.allocation_line_id.id
            line.amount = max(
                0.0,
                inst_alloc_by_line.get(lid, 0.0) - received_by_line.get(lid, 0.0),
            )

    def action_save(self):
        self.ensure_one()
        receipt = self.env["kris.project.receipt"].create(
            {
                "project_id": self.project_id.id,
                "installment_id": self.installment_id.id or False,
                "name": self.name,
                "date": self.date,
                "equipment_cost_in_installment": self.equipment_cost_in_installment,
                "amount": self.amount,
                "extra_income": self.extra_income,
                "note": self.note,
            }
        )
        for line in self.allocation_ids:
            self.env["kris.project.receipt.allocation"].create(
                {
                    "receipt_id": receipt.id,
                    "allocation_line_id": line.allocation_line_id.id,
                    "amount": line.amount,
                    "remaining_amount": line.remaining_amount,
                }
            )
        for att in self.wizard_attachment_ids:
            if att.file:
                self.env["ir.attachment"].create(
                    {
                        "name": att.filename or "untitled",
                        "datas": att.file,
                        "res_model": "kris.project.receipt",
                        "res_id": receipt.id,
                        "document_type_id": att.document_type_id.id or False,
                    }
                )
        return {"type": "ir.actions.act_window_close"}


class KrisProjectReceiptWizardLine(models.TransientModel):
    _name = "kris.project.receipt.wizard.line"
    _description = "KRIS Project Receipt Wizard Line"
    _order = "allocation_line_id"

    wizard_id = fields.Many2one(
        comodel_name="kris.project.receipt.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    allocation_line_id = fields.Many2one(
        comodel_name="kris.project.allocation.line",
        string="Allocation",
        required=True,
    )
    name = fields.Char(
        related="allocation_line_id.name",
        string="Allocator",
        readonly=True,
    )
    amount = fields.Monetary(string="Amount")
    remaining_amount = fields.Monetary(
        string="Remaining Amount",
        compute="_compute_remaining_amount",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="wizard_id.currency_id",
        readonly=True,
    )

    @api.depends(
        "allocation_line_id",
        "allocation_line_id.estimated_amount",
        "allocation_line_id.actual_amount",
    )
    def _compute_remaining_amount(self):
        for line in self:
            alloc = line.allocation_line_id
            line.remaining_amount = (
                alloc.estimated_amount - alloc.actual_amount if alloc else 0.0
            )


class KrisProjectReceiptWizardAttachment(models.TransientModel):
    _name = "kris.project.receipt.wizard.attachment"
    _description = "KRIS Project Receipt Wizard Attachment"

    wizard_id = fields.Many2one(
        comodel_name="kris.project.receipt.wizard",
        required=True,
        ondelete="cascade",
    )
    file = fields.Binary(
        string="File",
        required=True,
        attachment=False,
    )
    filename = fields.Char(string="Filename")
    document_type_id = fields.Many2one(
        comodel_name="kris.project.document.type",
        string="Document Type",
    )
