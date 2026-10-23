from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class KmitlProjectFloatingReturn(models.TransientModel):
    """โอนคืนงบลอย — a Floating Return (ADR-0011).

    The reverse of the จัดสรรงบประมาณ (งบลอย) wizard it inherits: confirming
    builds a ``budget.transfer`` FROM the project's coordinate (with its
    dimension) TO the Floating Budget pool covering the project's รหัสงบ + four
    dimensions — the very pool an allocation draws from, whichever transfer
    brought the money in — and posts it at once. Money reserved but not yet
    obligated is released from the project's reservation in the same move
    (budget ADR-0017). The ``pool_*`` fields describe that pool (the TO side
    here).
    """

    _name = "kmitl.project.floating.return"
    _inherit = "kmitl.project.floating.allocation"
    _description = "โอนคืนงบลอย"

    direction = fields.Char(default="return", readonly=True)

    def _project_movable(self):
        """What can leave the project's coordinate: its allocation minus the
        largest claim on it — obligated/consumed, or the total a document type
        (พ.1, ใบขออนุมัติ, ใบขอเบิก) is capped by. The unobligated reservation
        itself does not count: it is released in the same move."""
        project = self.project_id.sudo()
        claimed = max(amount for _label, amount in project._get_project_claims())
        return max(project.budget_amount - claimed, 0.0)

    @api.depends("project_id")
    def _compute_pool(self):
        # Back into the pool the allocation draws from (exact coordinate or the
        # coarser one above it), so the return never opens a pool nested with
        # it (budget ADR-0016); with no pool left, the project's own รหัสงบ +
        # four dimensions.
        super()._compute_pool()
        for wiz in self:
            project = wiz.project_id.sudo()
            if not (project.analytic_account_id and project.budget_account_id):
                wiz.update({"pool_found": False, "floating_available": 0.0})
                continue
            if not wiz.pool_found:
                distribution = self._project_floating_distribution(project)
                dims = (
                    self.env["budget.controller"].sudo()._parse_dimensions(distribution)
                )
                wiz.update(
                    {
                        "pool_found": True,
                        "pool_account_id": project.budget_account_id.id,
                        "pool_distribution": distribution,
                        "pool_dims": self._dim_rows(
                            dict(dims, account_id=project.budget_account_id)
                        ),
                    }
                )
            wiz.floating_available = wiz._project_movable()

    def _check_allowed(self):
        self.project_id._check_floating_return_allowed()

    def _check_amount(self):
        if float_compare(self.amount, 0.0, precision_digits=2) <= 0:
            raise UserError(_("กรุณาระบุจำนวนเงินที่ต้องการโอนคืนมากกว่า 0"))
        if float_compare(self.amount, self.floating_available, precision_digits=2) > 0:
            label, claimed = max(
                self.project_id.sudo()._get_project_claims(), key=lambda c: c[1]
            )
            raise UserError(
                _(
                    "จำนวนเงินเกินยอดที่โอนคืนได้ (%(cap)s) — กันไว้สำหรับ%(label)s %(claimed)s บาท"
                )
                % {
                    "cap": "{:,.2f}".format(self.floating_available),
                    "label": label,
                    "claimed": "{:,.2f}".format(claimed),
                }
            )

    def _prepare_transfer_vals(self):
        vals = super()._prepare_transfer_vals()
        project = self.project_id.sudo()
        vals.update(
            {
                "reason": self.note
                or _("โอนคืนงบลอยจากโครงการ %s")
                % " ".join(filter(None, [project.key, project.name])),
                "is_floating_allocation": False,
                "is_floating_return": True,
                "line_ids": [
                    Command.create(
                        {
                            "transfer_direction": "from",
                            "account_id": project.budget_account_id.id,
                            "amount": self.amount,
                            "analytic_distribution": project.analytic_distribution,
                        }
                    ),
                    Command.create(
                        {
                            "transfer_direction": "to",
                            "account_id": self.pool_account_id.id,
                            "amount": self.amount,
                            "analytic_distribution": self.pool_distribution,
                        }
                    ),
                ],
            }
        )
        return vals

    def _post_transfer_messages(self, transfer):
        transfer.message_post(
            body=_("โอนคืนงบลอยผ่านหน้าโครงการ (ไม่ผ่านกระบวนการขออนุมัติโอนงบประมาณ)")
        )
        self.project_id.sudo().message_post(
            body=_("โอนคืนงบลอย %(amount)s บาท — ใบโอน %(name)s")
            % {"amount": "{:,.2f}".format(self.amount), "name": transfer.name}
        )
