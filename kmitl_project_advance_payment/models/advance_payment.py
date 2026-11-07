from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import escape_psql


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    # Typed mirror of `reference` (same pattern as agx_approval_advance_payment);
    # the borrower names the project by its running number (`key`).
    kmitl_project_id = fields.Many2one(
        comodel_name="kmitl.project",
        string="Project",
        compute="_compute_kmitl_project_id",
        inverse="_inverse_kmitl_project_id",
        store=True,
        readonly=False,
        index=True,
        ondelete="restrict",
        compute_sudo=False,
        copy=False,
    )
    reference = fields.Reference(selection_add=[("kmitl.project", "Project")])
    project_line_ids = fields.One2many(
        "advance.payment.project.line", "advance_payment_id", copy=False
    )
    loan_amount = fields.Monetary(
        compute="_compute_loan_amount",
        store=True,
        readonly=False,
        precompute=True,
        default=0.0,
    )
    # Read by the project loan rules; sudo: the borrower cannot read the project.
    is_project_in_progress = fields.Boolean(
        compute="_compute_project_flags", compute_sudo=True
    )

    @api.depends("reference")
    def _compute_kmitl_project_id(self):
        for rec in self:
            ref = rec.reference
            rec.kmitl_project_id = ref if ref and ref._name == "kmitl.project" else False

    def _inverse_kmitl_project_id(self):
        for rec in self:
            if rec.kmitl_project_id:
                rec.reference = rec.kmitl_project_id
            elif rec.reference_model == "kmitl.project":
                rec.reference = False

    @api.depends("project_line_ids.amount", "reference_model")
    def _compute_loan_amount(self):
        for rec in self:
            if rec.reference_model == "kmitl.project":
                rec.loan_amount = sum(rec.project_line_ids.mapped("amount"))
            else:
                rec.loan_amount = rec.loan_amount

    @api.depends("kmitl_project_id.state")
    def _compute_project_flags(self):
        for rec in self:
            rec.is_project_in_progress = rec.kmitl_project_id.state == "in_progress"

    @api.onchange("loan_type_id")
    def _onchange_loan_type_id(self):
        super()._onchange_loan_type_id()
        if self.loan_type_id.reference_model != "kmitl.project":
            self.kmitl_project_id = False
            self.project_line_ids = False

    @api.onchange("reference")
    def _onchange_reference_drop_foreign_lines(self):
        """Items of a previously picked project no longer apply."""
        self.project_line_ids = self.project_line_ids.filtered(
            lambda line: line.project_line_id.sudo().project_id == self.reference
        )

    def _find_reference_by_number(self, number):
        if self.loan_type_id.reference_model != "kmitl.project":
            return super()._find_reference_by_number(number)
        number = (number or "").strip()
        if not number:
            return False
        found = (
            self.env["kmitl.project"]
            .sudo()
            .search(
                [("key", "=ilike", escape_psql(number))]
                + self._get_reference_type_domain(),
                limit=2,
            )
        )
        return found if len(found) == 1 else False

    @api.depends("reference")
    def _compute_reference_number(self):
        super()._compute_reference_number()
        for rec in self.filtered(lambda r: r.reference_model == "kmitl.project"):
            rec.reference_number = rec.reference.sudo().key

    def _prepare_vals_from_reference(self):
        """The amount comes from the items the borrower picks, not the project."""
        vals = super()._prepare_vals_from_reference()
        project = self.kmitl_project_id.sudo()
        if project:
            vals["loan_reason"] = project.name or ""
        return vals

    def _get_reference_summary(self):
        summary = super()._get_reference_summary()
        project = self.kmitl_project_id.sudo()
        if project:
            summary.update(
                subject=project.name,
                unit=project.department_analytic_id.display_name,
            )
        return summary

    def _get_source_commitment(self):
        """A project's budget is its live shared commitment."""
        self.ensure_one()
        project = self.kmitl_project_id.sudo()
        if project:
            return project.budget_commitment_ids.filtered(
                lambda c: c.state in ("reserved", "partial")
            )[:1]
        return super()._get_source_commitment()

    def action_load_project_lines(self):
        """Add a zero-amount row per borrowable expense item of the project."""
        for rec in self:
            project = rec.kmitl_project_id.sudo()
            if rec.state != "draft" or not project:
                raise UserError(_("เลือกโครงการก่อน (เฉพาะสัญญาฉบับร่าง)"))
            have = rec.project_line_ids.project_line_id
            rec.project_line_ids = [
                (0, 0, {"project_line_id": line.id})
                for line in project.expense_line_ids
                if line not in have and not line.is_loan_via_pr_only
            ]

    def _check_project_line_caps(self):
        """A hard limit, not a switchable rule: no item may be borrowed past
        its remaining amount. The lock serialises concurrent submits."""
        self.ensure_one()
        lines = self.project_line_ids.project_line_id.sudo()
        if lines:
            self.env.cr.execute(
                "SELECT id FROM project_budget_line WHERE id IN %s FOR UPDATE",
                (tuple(lines.ids),),
            )
            # Re-read what concurrent loans committed before the lock.
            lines.invalidate_recordset()
            self.env["advance.payment"].invalidate_model(["state"])
            self.project_line_ids.invalidate_recordset(
                ["remaining_amount", "exceeds_remaining"]
            )
        if lines and lines.project_id != self.kmitl_project_id.sudo():
            raise ValidationError(_("มีรายการที่ไม่ใช่ของโครงการที่อ้างอิง"))
        over = self.project_line_ids.filtered("exceeds_remaining")
        if over:
            raise ValidationError(
                _(
                    "ยอดยืมเกินวงเงินคงเหลือของรายการ: %s",
                    ", ".join(over.mapped("name")),
                )
            )

    def action_submit(self):
        for rec in self.filtered(lambda r: r.state == "draft"):
            # Drop the rows left at 0 so only borrowed items remain.
            rec.project_line_ids.filtered(lambda line: not line.amount).unlink()
            rec._check_project_line_caps()
        return super().action_submit()
