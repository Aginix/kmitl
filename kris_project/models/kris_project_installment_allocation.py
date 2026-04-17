from odoo import api, fields, models


class KrisProjectInstallmentAllocation(models.Model):
    _name = "kris.project.installment.allocation"
    _description = "KRIS Project Installment Allocation Breakdown"
    _order = "allocation_line_id"

    installment_id = fields.Many2one(
        comodel_name="kris.project.installment",
        string="Installment",
        required=True,
        ondelete="cascade",
        index=True,
    )
    allocation_line_id = fields.Many2one(
        comodel_name="kris.project.allocation.line",
        string="Allocation",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(
        related="allocation_line_id.name",
        string="Allocator",
        readonly=True,
    )
    estimated_amount = fields.Monetary(
        related="allocation_line_id.estimated_amount",
        string="Estimated Amount (Baht)",
        readonly=True,
    )
    allocated_amount = fields.Monetary(
        string="Allocated Amount",
        compute="_compute_allocated_amount",
        readonly=True,
    )
    remaining_amount = fields.Monetary(
        string="Remaining Amount",
        compute="_compute_allocated_amount",
        readonly=True,
    )
    amount = fields.Monetary(string="Amount")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="installment_id.currency_id",
        readonly=True,
    )

    @api.depends("allocation_line_id", "estimated_amount")
    def _compute_allocated_amount(self):
        alloc_line_ids = self.mapped("allocation_line_id").ids
        if not alloc_line_ids:
            for line in self:
                line.allocated_amount = 0.0
                line.remaining_amount = line.estimated_amount
            return
        # In edit mode, exclude the current installment's own saved allocations
        domain = [("allocation_line_id", "in", alloc_line_ids)]
        exclude_ids = [i for i in self.mapped("installment_id").ids if i]
        if exclude_ids:
            domain.append(("installment_id", "not in", exclude_ids))
        groups = self.env["kris.project.installment.allocation"].read_group(
            domain=domain,
            fields=["allocation_line_id", "amount:sum"],
            groupby=["allocation_line_id"],
        )
        allocated_by_id = {g["allocation_line_id"][0]: g["amount"] for g in groups}
        for line in self:
            if not line.allocation_line_id:
                line.allocated_amount = 0.0
                line.remaining_amount = 0.0
                continue
            allocated = allocated_by_id.get(line.allocation_line_id.id, 0.0)
            line.allocated_amount = allocated
            line.remaining_amount = line.estimated_amount - allocated
