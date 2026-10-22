from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class KmitlProjectFloatingReturnSource(models.TransientModel):
    """One Inflow Source of the project: the FROM coordinate of posted
    transfers into its dimension, net of what was already returned there."""

    _name = "kmitl.project.floating.return.source"
    _description = "แหล่งที่มาของเงินโครงการ"
    _order = "returnable desc, id"

    wizard_id = fields.Many2one(
        "kmitl.project.floating.return", required=True, ondelete="cascade"
    )
    name = fields.Char(required=True)
    account_id = fields.Many2one("budget.account", required=True)
    analytic_distribution = fields.Json()
    returnable = fields.Float(digits="Budget Precision")
    dims = fields.Char()


class KmitlProjectFloatingReturn(models.TransientModel):
    """โอนคืนงบลอย — a Floating Return (ADR-0011).

    The reverse of the จัดสรรงบประมาณ (งบลอย) wizard it inherits: the user picks
    one of the project's Inflow Sources and an amount; confirming builds a
    ``budget.transfer`` FROM the project's coordinate (with its dimension) TO
    that source and posts it at once. Money reserved but not yet obligated is
    released from the project's reservation in the same move (budget ADR-0017).
    The ``pool_*`` fields describe the chosen source (the TO side here).
    """

    _name = "kmitl.project.floating.return"
    _inherit = "kmitl.project.floating.allocation"
    _description = "โอนคืนงบลอย"

    direction = fields.Char(default="return", readonly=True)
    source_ids = fields.One2many(
        "kmitl.project.floating.return.source", "wizard_id", readonly=True
    )
    source_id = fields.Many2one(
        "kmitl.project.floating.return.source",
        string="คืนให้แหล่งที่มา",
        domain="[('wizard_id', '=', id)]",
    )

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        for wizard in wizards:
            wizard._load_sources()
        return wizards

    def _load_sources(self):
        """List the Inflow Sources and preselect the largest, with its full
        returnable amount."""
        sources = self.env["kmitl.project.floating.return.source"]
        for account, distribution, amount in self._inflow_sources(self.project_id):
            dims = dict(
                self.env["budget.controller"].sudo()._parse_dimensions(distribution),
                account_id=account,
            )
            unit = dims.get("department_analytic_id")
            sources |= sources.create(
                {
                    "wizard_id": self.id,
                    "name": "%s · [%s] %s — คืนได้ ฿%s"
                    % (
                        unit.display_name if unit else "-",
                        account.code,
                        account.name,
                        "{:,.2f}".format(amount),
                    ),
                    "account_id": account.id,
                    "analytic_distribution": distribution,
                    "returnable": amount,
                    "dims": self._dim_rows(dims),
                }
            )
        source = sources.sorted("returnable", reverse=True)[:1]
        if source:
            self.write({"source_id": source.id, "amount": self._cap(source)})

    @api.model
    def _inflow_sources(self, project):
        """``[(budget.account, distribution, returnable)]`` — every coordinate
        money came into the project's dimension from, through posted transfers
        in the project's fiscal year, net of what was returned there since.

        A transfer's FROM lines are credited to the project in proportion to
        its share of the TO side (exact for the usual one-pool → one-project
        transfer); a transfer out of the project debits its TO coordinates the
        same way. Money that came without a transfer (an appropriation or entry
        keyed straight onto the project) has no source to return to."""
        analytic = project.sudo().analytic_account_id
        if not analytic:
            return []
        transfers = (
            self.env["budget.transfer"]
            .sudo()
            .search(
                [
                    ("state", "=", "posted"),
                    ("account_fiscal_year_id", "=", project.account_fiscal_year_id.id),
                    ("line_ids.kmitl_project_analytic_id", "=", analytic.id),
                ]
            )
        )
        balance = defaultdict(float)
        coordinate = {}
        for transfer in transfers:
            lines = transfer.line_ids.filtered("transfer_direction")
            from_lines = lines.filtered(lambda line: line.transfer_direction == "from")
            to_lines = lines - from_lines
            ours = lines.filtered(
                lambda line: line.kmitl_project_analytic_id == analytic
            )
            for project_side, other_side, side, sign in (
                (to_lines & ours, from_lines - ours, to_lines, 1.0),
                (from_lines & ours, to_lines - ours, from_lines, -1.0),
            ):
                moved = sum(project_side.mapped("amount"))
                if not moved or not other_side:
                    continue
                # The project's share of this side of the transfer.
                share = moved / sum(side.mapped("amount"))
                for line in other_side:
                    distribution = dict(line.analytic_distribution or {})
                    key = (line.account_id.id, tuple(sorted(distribution)))
                    coordinate[key] = (line.account_id, distribution)
                    balance[key] += sign * line.amount * share
        return [
            (coordinate[key][0], coordinate[key][1], amount)
            for key, amount in balance.items()
            if float_compare(amount, 0.0, precision_digits=2) > 0
        ]

    def _project_movable(self):
        """What can leave the project's coordinate: its allocation minus what
        its reservations already obligated or spent."""
        project = self.project_id.sudo()
        used = sum(
            project.budget_commitment_ids.filtered(
                lambda c: c.state != "cancel"
            ).mapped("total_obligated")
        )
        return max(project.budget_amount - used, 0.0)

    def _cap(self, source):
        return min(source.returnable, self._project_movable())

    @api.depends("project_id", "source_id")
    def _compute_pool(self):
        for wiz in self:
            source = wiz.source_id
            wiz.update(
                {
                    "pool_found": bool(wiz.source_ids),
                    "pool_account_id": source.account_id.id,
                    "pool_distribution": source.analytic_distribution or False,
                    "pool_dims": source.dims or "[]",
                    "floating_available": wiz._cap(source) if source else 0.0,
                }
            )

    def _check_allowed(self):
        self.project_id._check_floating_return_allowed()

    def _check_amount(self):
        if float_compare(self.amount, 0.0, precision_digits=2) <= 0:
            raise UserError(_("กรุณาระบุจำนวนเงินที่ต้องการโอนคืนมากกว่า 0"))
        if not self.source_id:
            raise UserError(
                _("ไม่พบแหล่งที่มาของเงินที่โอนคืนได้ กรุณาทำใบโอนงบประมาณตามขั้นตอนปกติ")
            )
        if float_compare(self.amount, self.floating_available, precision_digits=2) > 0:
            raise UserError(
                _("จำนวนเงินเกินยอดที่โอนคืนได้ (%s)")
                % "{:,.2f}".format(self.floating_available)
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
                            "account_id": self.source_id.account_id.id,
                            "amount": self.amount,
                            "analytic_distribution": self.source_id.analytic_distribution,
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
