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
    available_installment_ids = fields.Many2many(
        comodel_name="kris.project.installment",
        string="งวดที่ใช้ได้",
        compute="_compute_available_installment_ids",
    )
    installment_id = fields.Many2one(
        comodel_name="kris.project.installment",
        string="Installment Number",
        domain="[('id', 'in', available_installment_ids)]",
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
        string="ค่า Extra",
    )
    allocation_ids = fields.One2many(
        comodel_name="kris.project.receipt.wizard.line",
        inverse_name="wizard_id",
        string="Allocation",
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

    @api.depends("project_id", "project_id.receipt_ids.installment_id")
    def _compute_available_installment_ids(self):
        for wiz in self:
            used_ids = wiz.project_id.receipt_ids.mapped("installment_id").ids
            available = wiz.project_id.installment_ids.filtered(
                lambda i: i.id not in used_ids
            )
            wiz.available_installment_ids = available

    @api.depends("amount", "equipment_cost_in_installment")
    def _compute_net_amount(self):
        for wiz in self:
            wiz.net_amount = wiz.amount - wiz.equipment_cost_in_installment

    # def _fill_allocation_proportionally(self):
    #     base = self.project_id.maintenance_deduction_amount
    #     net = self.net_amount
    #     for line in self.allocation_ids:
    #         if base and line.allocation_line_id:
    #             ratio = line.allocation_line_id.estimated_amount / base
    #             line.amount = net * ratio
    #         else:
    #             line.amount = 0.0

    # @api.onchange("amount", "equipment_cost_in_installment")
    # def _onchange_amount(self):
    #     self._fill_allocation_proportionally()

    # @api.onchange("installment_id")
    # def _onchange_installment_id(self):
    #     if self.installment_id:
    #         self.amount = self.installment_id.amount
    #         self.extra_income = self.installment_id.extra_income
    #         self._fill_allocation_proportionally()

    @api.onchange("installment_id")
    def _onchange_installment_id(self):
        if self.installment_id:
            self.amount = self.installment_id.amount
            self.extra_income = self.installment_id.extra_income
            inst_alloc_by_line = {
                ia.allocation_line_id.id: ia.amount
                for ia in self.installment_id.allocation_ids
            }
            for line in self.allocation_ids:
                line.amount = inst_alloc_by_line.get(line.allocation_line_id.id, 0.0)

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
        string="จำนวนเงินคงค้าง",
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
        "allocation_line_id.receipt_allocation_ids.amount",
        "amount",
    )
    def _compute_remaining_amount(self):
        for line in self:
            alloc = line.allocation_line_id
            if not alloc:
                line.remaining_amount = 0.0
                continue
            already_received = sum(alloc.receipt_allocation_ids.mapped("amount"))
            line.remaining_amount = alloc.estimated_amount - already_received - line.amount
