from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    kmitl_project_id = fields.Many2one(
        comodel_name="kmitl.project",
        string="โครงการ/กิจกรรม",
        domain=[("state", "=", "in_progress")],
        states={
            "purchase": [("readonly", True)],
            "done": [("readonly", True)],
            "cancel": [("readonly", True)],
        },
        copy=False,
        tracking=True,
        inverse="_inverse_kmitl_project_id",
        help="โครงการที่ใบสั่งซื้อนี้หยิบใบจองงบประมาณไปใช้",
    )

    # Keep the project dimension in analytic_distribution: the mixin rebuilds the
    # distribution from its known dimension fields, so an unknown kmitl_project
    # account would be dropped. A plain (non-computed) field, filled by the
    # mixin's inverse from analytic_distribution, so installing this module does
    # not recompute — and rewrite — the distribution of every existing order.
    kmitl_project_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="โครงการ/กิจกรรม (Analytic)",
        domain=[("root_plan_id.code", "=", "kmitl_project")],
        copy=True,
    )

    def _analytic_fields(self):
        fields_list = super()._analytic_fields()
        fields_list.append("kmitl_project_analytic_id")
        return fields_list

    def _analytic_keys(self):
        res = super()._analytic_keys()
        res["kmitl_project"] = "kmitl_project_analytic_id"
        return res

    def _budget_commitment_mode_domain(self):
        # A project's commitment is reached only through the project picker.
        return super()._budget_commitment_mode_domain() + [
            ("kmitl_project_id", "=", False)
        ]

    def _kmitl_project_commitment(self):
        return self.kmitl_project_id.budget_commitment_ids.filtered(
            lambda c: c.state in ("reserved", "partial")
        )[:1]

    @api.onchange("kmitl_project_id")
    def _onchange_kmitl_project_id(self):
        if self.kmitl_project_id:
            self.budget_commitment_id = self._kmitl_project_commitment()
        elif self.budget_commitment_id.kmitl_project_id:
            self.budget_commitment_id = False

    def _inverse_kmitl_project_id(self):
        """Server-side: the commitment field is locked on the form once a
        project is picked, so the project — not the client — decides it."""
        for rec in self.filtered("kmitl_project_id"):
            commitment = rec._kmitl_project_commitment()
            if rec.budget_commitment_id != commitment:
                rec.budget_commitment_id = commitment

    @api.onchange("budget_commitment_id")
    def _onchange_budget_commitment_id(self):
        res = super()._onchange_budget_commitment_id()
        if self.budget_commitment_id:
            self.kmitl_project_analytic_id = (
                self.budget_commitment_id.kmitl_project_analytic_id.id
            )
        return res

    def _check_standalone_project_budget(self):
        """A standalone PO drawing a project's shared commitment must stay within
        the project's reserved budget, net of what its purchase requests and
        other confirmed standalone POs already claim (cf. the PR-side
        ``_enforce_project_budget_cap``)."""
        for rec in self.filtered(lambda r: r.kmitl_project_id and not r.request_id):
            project = rec.kmitl_project_id
            if project.state != "in_progress":
                raise UserError(
                    _(
                        "โครงการ %s ยังไม่ได้รับอนุมัติและกำลังดำเนินการ "
                        "จึงยังใช้ใบจองงบประมาณของโครงการไม่ได้"
                    )
                    % project.display_name
                )
            if not rec.budget_commitment_id:
                raise UserError(_("โครงการยังไม่ได้จองงบประมาณ ไม่สามารถดำเนินการได้"))
            if rec.budget_commitment_id.kmitl_project_id != project:
                raise UserError(
                    _("ใบจองงบประมาณที่เลือกไม่ใช่ของโครงการ %s")
                    % project.display_name
                )
            other_pos = self.search(
                [
                    ("kmitl_project_id", "=", project.id),
                    ("state", "in", ("purchase", "done")),
                    ("id", "!=", rec.id),
                ]
            )
            remaining = (
                project.budget_amount
                - project._project_pr_total()
                - sum(other_pos.mapped("amount_total"))
            )
            if (
                float_compare(
                    rec.amount_total,
                    remaining,
                    precision_rounding=rec.currency_id.rounding,
                )
                > 0
            ):
                raise UserError(
                    _(
                        "ใบสั่งซื้อนี้ (%(amount)s) เกินงบประมาณคงเหลือของโครงการ "
                        "(คงเหลือ %(remaining)s จากงบ %(budget)s)"
                    )
                    % {
                        "amount": "{:,.2f}".format(rec.amount_total),
                        "remaining": "{:,.2f}".format(remaining),
                        "budget": "{:,.2f}".format(project.budget_amount),
                    }
                )

    def button_confirm(self):
        self._check_standalone_project_budget()
        return super().button_confirm()
