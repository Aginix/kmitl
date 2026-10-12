from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class KmitlProjectDirectAllocation(models.TransientModel):
    """Direct Allocation (จัดสรรจากเงินลอย, ADR-0009).

    For a project whose budget was already approved with its floating money at
    ประมาณการรายจ่าย, งานแผน allocates and reserves in one step: a budget
    transfer FROM the floating pool at the project's own coordinate TO the same
    coordinate + the project dimension is posted at once, without the transfer's
    approval (e-Saraban), then the project reserves as usual (to_verify → to_send).
    """

    _name = "kmitl.project.direct.allocation"
    _description = "จัดสรรและจองงบประมาณ (จัดสรรจากเงินลอย)"

    project_id = fields.Many2one("kmitl.project", required=True, readonly=True)
    budget_account_id = fields.Many2one(related="project_id.budget_account_id")
    account_fiscal_year_id = fields.Many2one(
        related="project_id.account_fiscal_year_id"
    )
    department_analytic_id = fields.Many2one(
        related="project_id.department_analytic_id"
    )
    source_analytic_id = fields.Many2one(related="project_id.source_analytic_id")
    activity_analytic_id = fields.Many2one(related="project_id.activity_analytic_id")
    fund_analytic_id = fields.Many2one(related="project_id.fund_analytic_id")
    analytic_account_id = fields.Many2one(related="project_id.analytic_account_id")
    budget_amount = fields.Float(related="project_id.budget_amount")
    amount = fields.Float(string="จำนวนเงินที่จัดสรร", digits="Budget Precision")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        project = self.env["kmitl.project"].browse(res.get("project_id"))
        if project and "amount" in fields_list:
            res["amount"] = max(project.budget_expense_total - project.budget_amount, 0)
        return res

    def action_confirm(self):
        self.ensure_one()
        if not (
            self.env.user.has_group("budget.group_budget_user") or self.env.is_admin()
        ):
            raise UserError(_("เฉพาะเจ้าหน้าที่งบประมาณ (Budget User) เท่านั้น"))
        project = self.project_id
        if project.state != "to_verify":
            raise UserError(_("จัดสรรและจองงบประมาณได้เฉพาะสถานะรอจัดสรรงบประมาณ"))
        if self.amount < 0:
            raise UserError(_("จำนวนเงินที่จัดสรรต้องไม่ติดลบ"))
        transfer = self._post_floating_transfer() if self.amount else False
        self.env["kmitl.project.reserve.confirm"].create(
            {"project_id": project.id}
        ).action_confirm()
        if transfer:
            project.message_post(
                body=Markup(
                    _(
                        "จัดสรรจากเงินลอย %s จำนวน %s บาท "
                        "(อนุมัติแล้วตอนประมาณการรายจ่าย — ไม่ผ่านขั้นตอนอนุมัติใบโอน)"
                    )
                )
                % (transfer._get_html_link(), "{:,.2f}".format(self.amount))
            )

    def _post_floating_transfer(self):
        """Create and post the floating → project-dimension transfer. Keeps every
        check of ยืนยัน (structure, exception rules, availability); skips only the
        approval — base ``action_approve`` is Budget-Manager/not-self, so post
        through ``_post_transfer`` directly."""
        project = self.project_id
        line = {
            "account_id": project.budget_account_id.id,
            "amount": self.amount,
            "activity_analytic_id": project.activity_analytic_id.id,
            "department_analytic_id": project.department_analytic_id.id,
            "fund_analytic_id": project.fund_analytic_id.id,
        }
        transfer = self.env["budget.transfer"].create(
            {
                "date": fields.Date.context_today(self),
                "account_fiscal_year_id": project.account_fiscal_year_id.id,
                "department_analytic_id": project.department_analytic_id.id,
                "source_analytic_id": project.source_analytic_id.id,
                "reason": _("จัดสรรจากเงินลอย (อนุมัติแล้วตอนประมาณการรายจ่าย) — [%s] %s")
                % (project.key, project.name),
                "line_ids": [
                    (0, 0, dict(line, transfer_direction="from")),
                    (
                        0,
                        0,
                        dict(
                            line,
                            transfer_direction="to",
                            kmitl_project_analytic_id=project.analytic_account_id.id,
                        ),
                    ),
                ],
            }
        )
        transfer.action_submit()
        if transfer.state != "submitted":
            # budget_transfer_exception returned its popup instead of raising.
            names = (
                transfer.exception_ids.mapped("name")
                if "exception_ids" in transfer._fields
                else []
            )
            raise UserError(_("ใบโอนงบประมาณไม่ผ่านการตรวจสอบ:\n%s") % "\n".join(names))
        transfer.write(
            {"approver_id": self.env.user.id, "approval_date": fields.Datetime.now()}
        )
        transfer._post_transfer()
        return transfer
