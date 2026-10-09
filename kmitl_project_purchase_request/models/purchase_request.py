import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    use_project = fields.Boolean(
        string="Use KMITL Project",
        store=True,
    )

    budget_selection_mode = fields.Selection(
        selection_add=[("project", "โครงการ/กิจกรรม")],
        ondelete={"project": "set default"},
    )

    kmitl_project_id = fields.Many2one(
        comodel_name="kmitl.project",
        string="โครงการ/กิจกรรม",
        tracking=True,
        # Pickable once the project's money is reserved (to_send onwards) and
        # in the request's own fiscal year — Reserve still waits for
        # in_progress (root ADR-0011). OU scoping comes from the global
        # kmitl.project rule.
        domain="[('state', 'in', ('to_send', 'sent', 'in_progress')),"
        " ('account_fiscal_year_id', '=', account_fiscal_year_id),"
        " ('budget_account_id.purchase_ok', '=', True),"
        " ('budget_account_id.product_id', '!=', False)]",
    )
    kmitl_project_remaining = fields.Float(
        string="งบโครงการคงเหลือ",
        digits="Product Price",
        compute="_compute_kmitl_project_remaining",
        help=(
            "งบประมาณของโครงการ หักใบขอซื้อที่จองงบประมาณแล้ว — ใบนี้ยังไม่ถูกนับ"
            "จนกว่าจะจองงบประมาณ (ข้อมูลประกอบเท่านั้น, root ADR-0011)"
        ),
    )

    project_analytic_id = fields.Many2one(
        "account.analytic.account",
        compute="_compute_project_analytic_id",
        inverse="_inverse_project_analytic",
        domain=[("root_plan_id.code", "=", "kmitl_project")],
        store=False,
        string="โครงการ/กิจกรรม (Analytic)",
    )

    @api.depends("analytic_distribution")
    def _compute_project_analytic_id(self):
        for rec in self:
            account_ids = [int(a) for a in rec.analytic_distribution or {}]
            accounts = self.env["account.analytic.account"].browse(account_ids)
            rec.project_analytic_id = accounts.filtered(
                lambda a: a.plan_id.code == "kmitl_project"
            )[:1]

    def _inverse_project_analytic(self):
        for rec in self:
            dist = dict(rec.analytic_distribution or {})
            account_ids = [int(k) for k in dist.keys()]
            accounts = self.env["account.analytic.account"].browse(account_ids)
            for acc in accounts.filtered(lambda a: a.plan_id.code == "kmitl_project"):
                dist.pop(str(acc.id), None)
            if rec.project_analytic_id:
                dist[str(rec.project_analytic_id.id)] = 100
            rec.analytic_distribution = dist or False

    @api.depends("kmitl_project_id")
    def _compute_kmitl_project_remaining(self):
        for rec in self:
            project = rec.kmitl_project_id
            rec.kmitl_project_remaining = (
                project.budget_amount - project._project_pr_total() if project else 0.0
            )

    def _domain_budget_account_id(self):
        # Standalone PRs must not draw directly on a project budget code — those
        # are reserved through projects (ADR-0007). Project-driven PRs prefill the
        # code (read-only), so the domain never blocks them.
        return super()._domain_budget_account_id() + [("is_project", "=", False)]

    def _procurement_under_fields(self):
        return super()._procurement_under_fields() | {"kmitl_project_id"}

    def _prepare_procurement_under_vals(self):
        """A chosen project brings its budget code, fiscal year and full
        analytic distribution (4 dims + its own kmitl_project dim), locked —
        root ADR-0011. The mode is the answer, the project only its detail:
        any other mode drops the project, never the other way round."""
        vals = super()._prepare_procurement_under_vals()
        project = self.kmitl_project_id
        if project and self.budget_selection_mode == "project":
            vals.update(
                {
                    "use_project": True,
                    "budget_account_id": project.budget_account_id.id,
                    "account_fiscal_year_id": project.account_fiscal_year_id.id,
                    "analytic_distribution": project.analytic_distribution or False,
                }
            )
        elif project:
            vals.update({"kmitl_project_id": False, "use_project": False})
        elif self.use_project:
            vals["use_project"] = False
        return vals

    @api.onchange("budget_selection_mode")
    def _onchange_budget_selection_mode_project(self):
        if self.budget_selection_mode != "project":
            self.kmitl_project_id = False

    @api.onchange("kmitl_project_id")
    def _onchange_kmitl_project_id(self):
        """Preview the project's code on the live form; the dimensions are
        written server-side (see _sync_procurement_under)."""
        project = self.kmitl_project_id
        if project:
            self.budget_account_id = project.budget_account_id.id
            if not self.title:
                self.title = project.name

    @api.onchange("account_fiscal_year_id")
    def _onchange_account_fiscal_year_id_project(self):
        # The year filters the project dropdown: another year drops the pick.
        project = self.kmitl_project_id
        if project and project.account_fiscal_year_id != self.account_fiscal_year_id:
            self.kmitl_project_id = False
            self.budget_account_id = False

    def _check_drawable_commitment(self, commitment):
        # A project's shared commitment sits on an ``is_project`` budget code this
        # PR may not *reserve new* on (ADR-0007), so the base gate — which mirrors
        # the full reserve-new field domain — would reject it. Drawing it down is
        # allowed, but the code must still be a purchasable, product-backed PR
        # budget code just like a directly selected one: check it against the base
        # domain (purchase_ok + product), lifting only the ``is_project`` exclusion.
        if commitment.kmitl_project_id:
            if not self.env["budget.account"].search_count(
                super()._domain_budget_account_id()
                + [("id", "=", commitment.account_id.id)]
            ):
                raise UserError(_("รหัสงบประมาณของใบจองที่เลือกไม่สามารถใช้กับเอกสารนี้ได้"))
            return True
        return super()._check_drawable_commitment(commitment)

    @api.depends("state", "use_project", "kmitl_project_id")
    def _compute_is_budget_editable(self):
        super()._compute_is_budget_editable()
        for rec in self:
            # A project พ.1's code and dims are the project's, in every state:
            # correcting them means changing the project (root ADR-0011).
            if rec.use_project:
                rec.is_budget_editable = False

    def action_view_kmitl_project(self):
        self.ensure_one()
        if not self.kmitl_project_id:
            return {"type": "ir.actions.act_window_close"}
        return {
            "type": "ir.actions.act_window",
            "res_model": "kmitl.project",
            "view_mode": "form",
            "res_id": self.kmitl_project_id.id,
            "target": "current",
        }

    def _enforce_project_budget_cap(self, project):
        """Raise if drawing this PR would push the project's drawn total over
        its reserved ``budget_amount`` (ADR-0007). Only PRs that have drawn
        count — this one is about to (root ADR-0011)."""
        others = project._project_pr_total(exclude=self)
        this_pr = sum(self.line_ids.mapped("estimated_cost"))
        if others + this_pr > project.budget_amount:
            raise UserError(
                _("ใบขอซื้อนี้ (%s) เกินงบประมาณคงเหลือของโครงการ (คงเหลือ %s จากงบ %s)")
                % (
                    "{:,.2f}".format(this_pr),
                    "{:,.2f}".format(project.budget_amount - others),
                    "{:,.2f}".format(project.budget_amount),
                )
            )

    def action_reserve_budget(self):
        """A project พ.1 names the project, not its ใบจอง (root ADR-0011): find
        the project's single live commitment and draw it through the base
        draw-down path, which re-takes code/dims/FY from it. Many PRs may share
        it, capped at the project's reserved budget_amount (ADR-0007)."""
        self.ensure_one()
        project = self.kmitl_project_id
        if project:
            self._check_can_commit_budget()
            self._check_project_drawable(project)
            commitment = project.sudo().budget_commitment_ids.filtered(
                lambda c: c.state in ("reserved", "partial")
            )[:1]
            if not commitment:
                raise UserError(_("โครงการยังไม่ได้จองงบประมาณ ไม่สามารถดำเนินการได้"))
            self.reservation_commitment_id = commitment.id
        return super().action_reserve_budget()

    def _check_project_drawable(self, project):
        """A พ.1 may wait on a project whose หนังสือ is not yet signed, but may
        draw only once the project is approved and executing (kmitl_project
        ADR-0005, root ADR-0011)."""
        if project.state != "in_progress":
            state = dict(project._fields["state"]._description_selection(self.env)).get(
                project.state, project.state
            )
            raise UserError(
                _(
                    "โครงการ %(project)s อยู่สถานะ '%(state)s' — ต้องรอให้โครงการ"
                    "ได้รับอนุมัติและกำลังดำเนินการก่อน จึงจองงบประมาณได้"
                )
                % {"project": project.display_name, "state": state}
            )

    def _action_draw_from_reservation(self):
        """Draw a project's shared commitment: gate on the project's approval,
        link the project, enforce its budget cap, then run the base draw — which
        copies the commitment's dims/account/FY onto the PR + lines, validates
        via the already-overridden ``_check_drawable_commitment``, and advances
        state. Also the backstop for a slip injected over RPC."""
        project = self.reservation_commitment_id.kmitl_project_id
        if project:
            self._check_project_drawable(project)
            if self.kmitl_project_id != project:
                self.write({"kmitl_project_id": project.id})
            self._enforce_project_budget_cap(project)
        return super()._action_draw_from_reservation()

    def _release_commitment_on_draft(self):
        """ดึงกลับ (Reset) keeps a project's shared commitment: the request is
        recalled to be edited, not to give up the project's budget. The commitment
        is released only on ยกเลิก (Cancel) — see _cancel_budget_commitment."""
        self.ensure_one()
        if self.budget_commitment_id.kmitl_project_id:
            return False
        return super()._release_commitment_on_draft()

    def _cancel_budget_commitment(self):
        """Detach — never cancel — a shared project commitment when a project PR is
        cancelled or rejected: just release this PR's hold on it (frees its
        headroom). ดึงกลับ (Reset) keeps it (see _release_commitment_on_draft)."""
        self.ensure_one()
        commitment = self.budget_commitment_id
        if commitment and commitment.kmitl_project_id:
            self.write(
                {"budget_commitment_id": False, "reservation_commitment_id": False}
            )
            return True
        return super()._cancel_budget_commitment()


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    purchase_request_ids = fields.One2many(
        comodel_name="purchase.request",
        inverse_name="kmitl_project_id",
        string="ใบขอซื้อ (พ.1)",
    )
    purchase_request_count = fields.Integer(compute="_compute_purchase_request_count")

    @api.depends("purchase_request_ids")
    def _compute_purchase_request_count(self):
        for record in self:
            record.purchase_request_count = len(record.purchase_request_ids)

    def _project_pr_total(self, exclude=None):
        """Total estimated cost of the project's purchase requests that have
        drawn its money (passed Reserve) — a พ.1 that only names the project
        does not count yet (root ADR-0011). Cancel/reject detach the commitment,
        so terminal PRs drop out on their own. sudo: PR record rules would hide
        other requesters' พ.1."""
        self.ensure_one()
        project = self.sudo()
        commitments = project.budget_commitment_ids
        drawn = project.purchase_request_ids.filtered(
            lambda r: r.budget_commitment_id in commitments
        )
        if exclude:
            drawn = drawn.filtered(lambda r: r.id not in exclude.ids)
        return sum(drawn.mapped("line_ids.estimated_cost"))

    def action_view_purchase_requests(self):
        self.ensure_one()
        action = {
            "name": _("ใบขอซื้อ (พ.1)"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.request",
            "domain": [("id", "in", self.purchase_request_ids.ids)],
        }
        if len(self.purchase_request_ids) == 1:
            action.update({"view_mode": "form", "res_id": self.purchase_request_ids.id})
        else:
            action["view_mode"] = "tree,form"
        return action
