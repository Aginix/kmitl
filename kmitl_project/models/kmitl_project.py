# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class KmitlProject(models.Model):
    _name = "kmitl.project"
    _description = "KMITL Project"
    _order = "id desc"
    _rec_names_search = ["name", "key"]
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "analytic.mixin",
        "portal.mixin",
        "budget.commitment.mixin",
    ]

    # Fields carrying the budget code / budget dimensions are editable only while
    # the project is being authored (draft) or has been sent back for revision
    # (returned) — readonly once it enters the approval band and thereafter.
    READONLY_STATES = {
        "to_verify": [("readonly", True)],
        "to_send": [("readonly", True)],
        "sent": [("readonly", True)],
        "rejected": [("readonly", True)],
        "in_progress": [("readonly", True)],
        "complete": [("readonly", True)],
        "cancel": [("readonly", True)],
    }
    # The two states in which the whole form is open for editing: draft authoring
    # and ตีกลับ/ดึงกลับ revision. Used as the per-field ``states=`` override in
    # place of the old draft-only rule.
    EDITABLE_STATES = {
        "draft": [("readonly", False)],
        "returned": [("readonly", False)],
    }

    name = fields.Char(
        "Name",
        tracking=True,
        required=True,
        readonly=True,
        states=EDITABLE_STATES,
    )
    project_type = fields.Selection(
        [("project", "Project/Activity"), ("strategic_project", "Strategic Project")],
        required=True,
        default="project",
        readonly=True,
        states=EDITABLE_STATES,
    )
    introduction = fields.Text(
        string="หลักการและเหตุผล",
        tracking=True,
        readonly=False,
        states={"complete": [("readonly", True)]},
    )
    objective = fields.Text(
        string="วัตถุประสงค์",
        tracking=True,
        readonly=True,
        states=EDITABLE_STATES,
    )

    national_strategy_id = fields.Many2one(
        "project.strategic.plan",
        string="ยุทธศาสตร์ชาติ",
        domain="[('level', '=', 1)]",
        tracking=True,
        readonly=True,
        states=EDITABLE_STATES,
    )

    master_plan_id = fields.Many2one(
        "project.strategic.plan",
        string="แผนแม่บทภายใต้ยุทธศาสตร์ชาติ",
        domain="[('level', '=', 2)]",
        tracking=True,
        readonly=True,
        states=EDITABLE_STATES,
    )

    nesdc_plan_id = fields.Many2one(
        "project.strategic.plan",
        string="แผนพัฒนาเศรษฐกิจและสังคมแห่งชาติ ฉบับที่ 13",
        domain=lambda self: [("id", "child_of", self.env.ref("kmitl_project.P13").id)],
        tracking=True,
        readonly=True,
        states=EDITABLE_STATES,
    )

    kmitl_plan_id = fields.Many2one(
        "project.strategic.plan",
        string="แผนกลยุทธสถาบัน",
        domain="[('level', '=', 3)]",
        tracking=True,
        readonly=True,
        states=EDITABLE_STATES,
    )

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    location = fields.Text(string="สถานที่/พื้นที่ดำเนินโครงการ", copy=True, tracking=True)
    key = fields.Char(
        string="เลขที่รันโครงการ",
        tracking=True,
        readonly=True,
        copy=False,
        help="เลขที่รันของโครงการ ออกให้ครั้งเดียวเมื่อส่งเข้าแผน "
        "และคงเดิมตลอดอายุโครงการ ใช้เป็นรหัส (code) ของมิติบัญชีโครงการ",
    )
    account_fiscal_year_id = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal year",
        required=True,
    )
    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
        readonly=True,
        states=EDITABLE_STATES,
    )
    manager_id = fields.Many2one(
        "hr.employee",
        string="หัวหน้าโครงการ",
        tracking=True,
        readonly=True,
        states=EDITABLE_STATES,
        help="พนักงานผู้เป็นหัวหน้า/ผู้จัดการโครงการ; สิทธิ์เข้าถึงของผู้ใช้ผูกผ่าน manager_id.user_id",
    )
    creating_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        readonly=True,
        copy=False,
    )
    date_start = fields.Date(
        string="Start Date",
        required=False,
        readonly=True,
        states=EDITABLE_STATES,
    )
    date_end = fields.Date(
        string="End Date",
        required=False,
        readonly=True,
        states=EDITABLE_STATES,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("to_verify", "รอจัดสรรงบประมาณ (ปรับเข้าแผน) และจองงบประมาณ"),
            ("to_send", "รอส่งขออนุมัติ"),
            ("sent", "ส่งขออนุมัติแล้ว"),
            ("returned", "ถูกตีกลับ"),
            ("rejected", "ถูกปฏิเสธ"),
            ("in_progress", "In Progress"),
            ("complete", "Completed"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        index=True,
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
    )

    impact_id = fields.Many2one(
        comodel_name="project.impact",
        string="Impact",
        copy=True,
        tracking=True,
        readonly=True,
        states=EDITABLE_STATES,
    )

    global_index_id = fields.Many2one(
        comodel_name="project.global.index",
        string="Global Index",
        copy=True,
        tracking=True,
        readonly=True,
        states=EDITABLE_STATES,
    )

    fight_id = fields.Many2one(
        comodel_name="project.fight",
        string="ความสอดคล้องกับค่านิยม : FIGHT",
        copy=True,
        tracking=True,
        readonly=True,
        states=EDITABLE_STATES,
    )

    methodology_ids = fields.Many2many(
        comodel_name="project.methodology",
        string="วิธีดำเนินการ",
        copy=True,
        tracking=True,
        readonly=False,
        states={"complete": [("readonly", True)]},
    )

    methodology_detail = fields.Text(
        "วิธีดำเนินการ (รายละเอียด)",
        copy=True,
        tracking=True,
        readonly=False,
        states={"complete": [("readonly", True)]},
    )

    target_ids = fields.One2many(
        "project.target",
        "project_id",
        string="กลุ่มเป้าหมาย/ผู้ดำเนินโครงการ",
        domain=[("line_type", "=", "target")],
        readonly=True,
        states=EDITABLE_STATES,
    )

    participant_ids = fields.One2many(
        "project.target",
        "project_id",
        string="กลุ่มเป้าหมาย/ผู้ดำเนินโครงการ",
        domain=[("line_type", "=", "participant")],
        readonly=True,
        states=EDITABLE_STATES,
    )

    organizer_ids = fields.One2many(
        "project.target",
        "project_id",
        string="กลุ่มเป้าหมาย/ผู้ดำเนินโครงการ",
        domain=[("line_type", "=", "organizer")],
        readonly=True,
        states=EDITABLE_STATES,
    )

    output_ids = fields.One2many(
        "project.output",
        "project_id",
        string="ผลผลิต",
        domain=[("line_type", "=", "output")],
        readonly=True,
        states=EDITABLE_STATES,
    )

    outcome_ids = fields.One2many(
        "project.output",
        "project_id",
        string="ผลลัพธ์",
        domain=[("line_type", "=", "outcome")],
        readonly=True,
        states=EDITABLE_STATES,
    )

    plan_ids = fields.One2many(
        "project.plan",
        "project_id",
        string="แผนการดำเนินงานและแผนการใช้จ่ายงบประมาณ",
        readonly=True,
        states=EDITABLE_STATES,
    )

    has_income = fields.Boolean(
        string="โครงการนี้มีรายรับ",
        help="ติ๊กเมื่อโครงการมีรายรับ (เช่น ค่าลงทะเบียน/เงินบริจาค/เงินรายได้) "
        "เพื่อแสดงตารางกรอกงบประมาณรายรับ; รายจ่ายจะแสดงเสมอ",
        readonly=True,
        states=EDITABLE_STATES,
    )

    income_line_ids = fields.One2many(
        "project.budget.line",
        "project_id",
        string="รายรับ",
        domain=[("budget_type", "=", "income")],
        readonly=True,
        states=EDITABLE_STATES,
    )

    @api.onchange("has_income")
    def _onchange_has_income(self):
        """Drop any income lines when the project is marked as having no income."""
        if not self.has_income:
            self.income_line_ids = [(5, 0, 0)]

    expense_line_ids = fields.One2many(
        "project.budget.line",
        "project_id",
        string="รายจ่าย",
        domain=[("budget_type", "=", "expense")],
        readonly=True,
        states=EDITABLE_STATES,
    )

    budget_income_total = fields.Float(
        string="รวมรายรับ",
        compute="_compute_budget_plan_totals",
        digits="Product Price",
    )
    budget_expense_total = fields.Float(
        string="รวมรายจ่าย",
        compute="_compute_budget_plan_totals",
        digits="Product Price",
    )

    @api.depends("income_line_ids.amount", "expense_line_ids.amount")
    def _compute_budget_plan_totals(self):
        for rec in self:
            rec.budget_income_total = sum(rec.income_line_ids.mapped("amount"))
            rec.budget_expense_total = sum(rec.expense_line_ids.mapped("amount"))

    def _portal_budget_tree(self, budget_type):
        """Flat render plan for the portal budget table, grouped into nested
        ประเภทงบ (project.budget.category) sections — mirrors the backend OWL tree
        (see static ``project_budget_table``). Returns an ordered list of rows::

            {"type": "header", "level": int, "name": str, "total": float}
            {"type": "line",   "level": int, "line": project.budget.line}

        The ancestry of each line is read from its ``category_parent_path`` (ids)
        and ``category_complete_name`` (labels); a header opens whenever the path
        diverges going down and carries the roll-up subtotal of its whole subtree.
        Lines are ordered so every subtree is contiguous and category-less lines
        (e.g. รายรับ, which carry no ประเภทงบ) fall at the end as flat rows.
        """
        self.ensure_one()
        lines = (
            self.expense_line_ids
            if budget_type == "expense"
            else self.income_line_ids
        )

        def chain(line):
            # [(id, name), ...] root-first; zips the id path with the "/"-joined
            # complete name (names are curated master data, free of " / ").
            ids = [p for p in (line.category_parent_path or "").split("/") if p]
            names = (
                line.category_complete_name.split(" / ")
                if line.category_complete_name
                else []
            )
            return list(zip(ids, names))

        def sort_key(line):
            ids = [
                int(p) for p in (line.category_parent_path or "").split("/") if p
            ]
            return (0 if ids else 1, ids, line.sequence, line.id)

        lines = lines.sorted(key=sort_key)

        # Roll-up subtotal per node: every line adds its amount to each ancestor.
        totals = {}
        for line in lines:
            for cid, _name in chain(line):
                totals[cid] = totals.get(cid, 0.0) + line.amount

        rows = []
        prev = []
        for line in lines:
            ch = chain(line)
            common = 0
            while (
                common < len(prev)
                and common < len(ch)
                and prev[common][0] == ch[common][0]
            ):
                common += 1
            for level in range(common, len(ch)):
                cid, name = ch[level]
                rows.append(
                    {
                        "type": "header",
                        "level": level,
                        "name": name,
                        "total": totals.get(cid, 0.0),
                    }
                )
            rows.append({"type": "line", "level": len(ch), "line": line})
            prev = ch
        return rows

    expected_outcome_ids = fields.One2many(
        "project.expected.outcome",
        "project_id",
        string="ผลที่คาดว่าจะได้รับ",
        readonly=True,
        states=EDITABLE_STATES,
    )

    evaluation_ids = fields.Many2many(
        comodel_name="project.evaluation",
        string="วิธีการ/เครื่องมือติดตามและประเมินผล",
        copy=True,
        tracking=True,
        readonly=True,
        states=EDITABLE_STATES,
    )

    evaluation_detail = fields.Text(
        "วิธีการ/เครื่องมือติดตามและประเมินผล (รายละเอียด)",
        copy=True,
        tracking=True,
        readonly=True,
        states=EDITABLE_STATES,
    )

    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Attachments",
    )

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        copy=False,
        inverse="_inverse_analytic_account_id",
        ondelete="set null",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        help="Analytic account to which this procurement plan. \n"
        "Track the costs and revenues of your procurement plan by setting this analytic account on your related documents (e.g. budgetings, purchase requests, purchase orders etc.).",
    )

    active = fields.Boolean(default=True)
    is_editable = fields.Boolean(compute="_compute_is_editable")

    budget_account_id = fields.Many2one(comodel_name="budget.account",
        string="รหัสงบประมาณ",
        index=True,
        tracking=True,
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense'),"
        " ('is_project', '=', True), ('project_type', '=', project_type)]",
        states=READONLY_STATES
    )

    budget_target_locked = fields.Boolean(
        compute="_compute_budget_target_locked",
        store=True,
    )

    budget_amount = fields.Float(
        string="งบประมาณ",
        digits="Product Price",
        tracking=True,
        compute="_compute_budget_amount",
        store=True,
        readonly=True,
        help="งบประมาณที่ได้รับจัดสรร คำนวณจากยอดจัดสรร (budget.move.line) ที่ติด kmitl_project dim",
    )

    budget_commitment_ids = fields.One2many(
        "budget.commitment",
        "kmitl_project_id",
        string="ผูกพันงบประมาณ",
        readonly=True,
        copy=False,
    )
    budget_commitment_count = fields.Integer(
        string="จำนวนผูกพันงบประมาณ",
        compute="_compute_budget_commitment_count",
    )
    budget_remaining = fields.Float(
        string="งบประมาณคงเหลือ",
        compute="_compute_budget_remaining",
        help="งบประมาณที่จองไว้ของโครงการ หักด้วยยอดที่เบิกจ่าย (ใช้) ไปแล้ว",
    )

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        # Stored so the project dashboard can search/group by department dimension
        # (replaces the removed hr.department department_id).
        store=True,
        tracking=True,
        states=READONLY_STATES,
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
        "kmitl_project": "analytic_account_id",
    }

    def _inverse_activity_analytic(self):
        """Update distribution when activity changes"""
        for line in self:
            line._update_analytic_distribution("activities")

    def _inverse_department_analytic(self):
        """Update distribution when department changes"""
        for line in self:
            line._update_analytic_distribution("departments")

    def _inverse_fund_analytic(self):
        """Update distribution when fund changes"""
        for line in self:
            line._update_analytic_distribution("funds")

    def _inverse_source_analytic(self):
        """Update distribution when fund changes"""
        for line in self:
            line._update_analytic_distribution("sources")

    def _inverse_analytic_account_id(self):
        """Update distribution when source changes"""
        for line in self:
            line._update_analytic_distribution("kmitl_project")

    def copy_data(self, default=None):
        """A duplicate is a fresh draft that has not reserved budget yet, so it
        must not inherit the source project's own analytic account. The scalar
        ``analytic_account_id`` is already ``copy=False``, but the inherited
        ``analytic_distribution`` JSON (``copy=True``) still carries the
        ``kmitl_project`` dimension pointing at the old account — strip that one
        key while keeping the other dimensions the user filled in."""
        vals_list = super().copy_data(default=default)
        for record, vals in zip(self, vals_list):
            acc_id = record.analytic_account_id.id
            if acc_id and "analytic_distribution" in vals:
                dist = dict(vals["analytic_distribution"] or {})
                dist.pop(str(acc_id), None)
                vals["analytic_distribution"] = dist or False
            if "name" not in (default or {}):
                vals["name"] = _("%s (copy)") % (record.name or "")
        return vals_list

    def action_confirm(self):
        """``draft`` → ``to_verify`` ("ส่งเข้าแผน"). Mints the Project Number,
        analytic account, and ปีงบ-freeze here — before the exception gate in
        kmitl_project_exception.py runs super() — so they only fire after the
        strategic-plan check passes."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("ยืนยันได้เฉพาะโครงการที่เป็นแบบร่าง"))
        self._ensure_analytic_account()
        self.write({"state": "to_verify"})

    def action_reserve_budget(self):
        """``to_verify`` → open the จองงบ confirm wizard. The wizard shows the
        รหัสงบ, 4 มิติ + มิติโครงการ, and the actual allocated amount; on confirm
        it reserves the commitment (with the project dimension in the check) and
        advances to ``to_send``. Gated: raises if no allocation exists yet."""
        self.ensure_one()
        if self.state != "to_verify":
            raise UserError(_("จองงบประมาณได้เฉพาะสถานะรอตรวจสอบ"))
        if self.budget_amount <= 0:
            raise UserError(
                _("ยังไม่ได้รับการจัดสรรงบประมาณ "
                  "กรุณารอให้งานแผนโอนงบเข้าโครงการก่อนจึงจะจองงบประมาณได้")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("จองงบประมาณ"),
            "res_model": "kmitl.project.reserve.confirm",
            "view_mode": "form",
            "target": "new",
            "context": {"default_project_id": self.id},
        }

    def action_approve(self):
        """Manual approval fallback for installs WITHOUT ``kmitl_project_sarabun``:
        ``to_send``/``sent`` → ``in_progress``. When the bridge is installed the
        project is approved by the หนังสือ outcome instead (the bridge overrides
        ``_on_sarabun_completed`` to call the same transition)."""
        self.ensure_one()
        if self.state not in ("to_send", "sent"):
            raise UserError(_("อนุมัติได้เฉพาะคำขอที่ส่งขออนุมัติแล้ว"))
        self.write({"state": "in_progress"})

    def action_complete(self):
        """``in_progress`` → ``complete`` (manual; leftover reserved budget is
        returned manually, not auto-released — see ADR-0005)."""
        self.ensure_one()
        if self.state != "in_progress":
            raise UserError(_("ปิดโครงการได้เฉพาะที่กำลังดำเนินการ"))
        self.write({"state": "complete"})

    def action_reject(self):
        """→ ``rejected`` and release the reservation. Reached from the หนังสือ
        ปฏิเสธ outcome (bridge ``_on_sarabun_rejected``) or manually. Only a project
        still inside the approval band can be rejected — an approved/executing or
        finished one is past the point of refusal."""
        if self.filtered(
            lambda p: p.state not in ("to_verify", "to_send", "sent", "returned")
        ):
            raise UserError(_("ปฏิเสธได้เฉพาะโครงการที่อยู่ระหว่างขออนุมัติ"))
        self._release_project_commitment()
        self.write({"state": "rejected"})

    def action_cancel(self):
        """→ ``cancel`` and release the reservation (kept once any obligate/
        consume exists). Blocked while a หนังสือ is circulating (``sent``) — the
        send must be pulled back / voided first so no live document is orphaned —
        and from ``complete`` (a finished project is not cancellable)."""
        if self.filtered(lambda p: p.state == "sent"):
            raise UserError(
                _("ไม่สามารถยกเลิกโครงการขณะหนังสือกำลังเวียนลงนาม "
                  "กรุณาดึงกลับหรือยกเลิกการส่งก่อน")
            )
        if self.filtered(lambda p: p.state == "complete"):
            raise UserError(_("ไม่สามารถยกเลิกโครงการที่ปิดแล้ว"))
        self._release_project_commitment()
        self.write({"state": "cancel"})

    def action_draft(self):
        """Reset to ``draft`` and release the reservation. Blocked from ``sent``
        (handle the หนังสือ first), ``in_progress`` and ``complete`` (no
        un-approving an executing/finished project)."""
        if self.filtered(lambda p: p.state in ("sent", "in_progress", "complete")):
            raise UserError(_("ไม่สามารถกลับเป็นแบบร่างจากสถานะนี้"))
        self._release_project_commitment()
        self.write({"state": "draft"})

    def _check_budget_plan_lines(self):
        """Validate the Project Budget Plan before the budget is reserved. Amounts
        may be left blank/zero while drafting, but every line must carry a positive
        amount before the project reserves its budget (called from
        ``action_reserve_budget``, and again from ``_resync_project_commitment``
        because ``returned`` reopens the plan for editing)."""
        self.ensure_one()
        lines = self.expense_line_ids
        if self.has_income:
            lines |= self.income_line_ids
        bad = lines.filtered(lambda line: line.amount <= 0)
        if bad:
            raise UserError(
                _(
                    "ไม่สามารถยืนยันโครงการได้ "
                    "เนื่องจากมีรายการงบประมาณที่ยังไม่ได้ระบุจำนวนเงิน (ต้องมากกว่า 0):\n%s"
                )
                % "\n".join(
                    "- %s" % (line.name or _("(ไม่ระบุรายการ)")) for line in bad
                )
            )

    def _compute_is_editable(self):
        for rec in self:
            if rec.state in ('draft', 'returned'):
                rec.is_editable = True
            else:
                rec.is_editable = False


    def unlink(self):
        for rec in self:
            if rec.state != "cancel":
                raise UserError(
                    _("You cannot delete a record. Please cancel the record first.")
                )
        return super().unlink()

    def action_preview_project(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/my/kmitl-project/%s' % self.id
        }

    def _compute_budget_commitment_count(self):
        for rec in self:
            rec.budget_commitment_count = len(rec.budget_commitment_ids)

    @api.depends(
        "budget_amount",
        "budget_commitment_ids.state",
        "budget_commitment_ids.total_consumed",
    )
    def _compute_budget_remaining(self):
        """Money left in the project = reserved budget − what has actually been
        consumed (เบิกจ่าย) from its commitment. Not the budget-account dashboard
        status — strictly this project's reservation vs its spend."""
        for rec in self:
            used = sum(
                rec.budget_commitment_ids.filtered(
                    lambda c: c.state != "cancel"
                ).mapped("total_consumed")
            )
            rec.budget_remaining = rec.budget_amount - used

    def action_open_budget_commitments(self):
        self.ensure_one()
        return {
            "name": _("ผูกพันงบประมาณ"),
            "type": "ir.actions.act_window",
            "res_model": "budget.commitment",
            "view_mode": "tree,form",
            "domain": [("kmitl_project_id", "=", self.id)],
        }

    def _budget_report_rows(self, lines):
        """Flat, ordered render plan for a budget table in the project proposal
        PDF — the server-side twin of the OWL table's ``renderRows`` (see
        project_budget_table.esm.js). Groups the given ``project.budget.line``
        records under their ประเภทงบ (project.budget.category) hierarchy: a
        ``header`` row opens each category level carrying its roll-up subtotal, and
        a ``line`` row renders each budget line under its deepest category.
        Category-less lines (e.g. income) render as flat level-0 lines.

        Returns an ordered list of dicts, each one of:
          {"type": "header", "level": int, "name": str, "total": float}
          {"type": "line", "level": int, "name": str,
           "description": str, "amount": float}
        """
        self.ensure_one()

        def chain(line):
            """Category ancestry root-first, e.g. [งบดำเนินงาน, ค่าตอบแทน]."""
            nodes = []
            cat = line.category_id
            while cat:
                nodes.append(cat)
                cat = cat.parent_id
            return list(reversed(nodes))

        # Order so every category subtree is contiguous (mirrors the line model's
        # own _order); category-less lines sink to the bottom.
        ordered = lines.sorted(
            key=lambda line: (
                line.category_id.parent_path or "~",
                line.sequence,
                line.id,
            )
        )
        # Roll-up total per category id: every line adds to each of its ancestors.
        totals = {}
        for line in lines:
            for cat in chain(line):
                totals[cat.id] = totals.get(cat.id, 0.0) + line.amount
        rows = []
        prev = []
        for line in ordered:
            nodes = chain(line)
            common = 0
            while (
                common < len(prev)
                and common < len(nodes)
                and prev[common].id == nodes[common].id
            ):
                common += 1
            for level in range(common, len(nodes)):
                node = nodes[level]
                rows.append(
                    {
                        "type": "header",
                        "level": level,
                        "name": node.name,
                        "total": totals.get(node.id, 0.0),
                    }
                )
            rows.append(
                {
                    "type": "line",
                    "level": len(nodes),
                    "name": line.name,
                    "description": line.description or "",
                    "amount": line.amount,
                }
            )
            prev = nodes
        return rows

    @api.model
    def _create_analytic_account_from_values(self, values):
        return self.env["account.analytic.account"].create(
            {
                "name": values.get("name", _("Unknown Analytic Account")),
                "code": values.get("code"),
                "company_id": self.env.company.id,
                "plan_id": self.env.ref(
                    "kmitl_project.analytic_plan_project",
                    raise_if_not_found=True,
                ).id,
            }
        )

    def _ensure_project_number(self):
        """Issue the project's running number (``key``) once, when it is first
        submitted (``draft→to_verify``, i.e. ส่งเข้าแผน). Idempotent — a later reset-to-draft keeps the
        number, never re-issues it. Stamped with the project's fiscal year (not the
        confirmation calendar date) by drawing the sequence on the fiscal year's
        end date, so the number always reads as its ปีงบประมาณ. Becomes the analytic
        account's ``code``."""
        self.ensure_one()
        if self.key:
            return
        self.key = self.env["ir.sequence"].next_by_code(
            "kmitl.project",
            sequence_date=self.account_fiscal_year_id.date_to,
        )

    def write(self, vals):
        """Freeze the budget-target group once a running number exists: the key,
        analytic, commitment, and allocation are all minted against
        ``account_fiscal_year_id`` + ``budget_account_id`` + the four budget
        dimensions at ส่งเข้าแผน — they must not drift afterwards (e.g. on the
        reset-to-draft edit path).

        ``analytic_distribution`` is partially guarded: adding or updating the
        kmitl_project key is allowed (needed by ``_ensure_analytic_account``),
        but changes to any other key (activity, department, fund, source) are
        blocked once the running number exists."""
        _LOCKED = frozenset(
            {"account_fiscal_year_id", "budget_account_id", "department_analytic_id"}
        )
        if _LOCKED & vals.keys():
            for rec in self:
                if not rec.key:
                    continue
                if (
                    "account_fiscal_year_id" in vals
                    and rec.account_fiscal_year_id.id != vals["account_fiscal_year_id"]
                ):
                    raise UserError(
                        _("ไม่สามารถเปลี่ยนปีงบประมาณได้ เนื่องจากโครงการมีเลขที่รันแล้ว (%s)")
                        % rec.key
                    )
                if (
                    "budget_account_id" in vals
                    and rec.budget_account_id.id != vals.get("budget_account_id")
                ):
                    raise UserError(
                        _("ไม่สามารถเปลี่ยนรหัสงบประมาณได้ เนื่องจากโครงการมีเลขที่รันแล้ว (%s)")
                        % rec.key
                    )
                if (
                    "department_analytic_id" in vals
                    and rec.department_analytic_id.id != vals.get("department_analytic_id")
                ):
                    raise UserError(
                        _("ไม่สามารถเปลี่ยนมิติส่วนงานได้ เนื่องจากโครงการมีเลขที่รันแล้ว (%s)")
                        % rec.key
                    )
        if "analytic_distribution" in vals:
            new_dist = vals.get("analytic_distribution") or {}
            for rec in self:
                if not rec.key:
                    continue
                old_dist = rec.analytic_distribution or {}
                # Allow the kmitl_project key to be added/updated; block changes
                # to any other budget-dimension key.
                proj_key = (
                    str(rec.analytic_account_id.id) if rec.analytic_account_id else None
                )
                for k in set(old_dist.keys()) | set(new_dist.keys()):
                    if k == proj_key:
                        continue
                    if old_dist.get(k) != new_dist.get(k):
                        raise UserError(
                            _(
                                "ไม่สามารถเปลี่ยนมิติงบประมาณได้ "
                                "เนื่องจากโครงการมีเลขที่รันแล้ว (%s)"
                            )
                            % rec.key
                        )
        return super().write(vals)

    def _ensure_analytic_account(self):
        """A confirmed project tracks its own ``kmitl_project`` analytic dimension so
        its reservation and downstream spend are attributable to the project. Create
        it on demand (kmitl.project, unlike procurement.plan, has no auto-create on
        write) and let the inverse fold it into ``analytic_distribution``."""
        self.ensure_one()
        self._ensure_project_number()
        if not self.analytic_account_id:
            self.analytic_account_id = self._create_analytic_account_from_values(
                {"name": self.name, "code": self.key}
            ).id
        # Fold the kmitl_project dimension into analytic_distribution — in both
        # branches, independent of the create-branch inverse-flush ordering. The
        # reservation picker rewrites analytic_distribution wholesale (the four
        # budget dimensions) on (re-)selection, dropping this dimension; refold it
        # so the reservation always carries the kmitl_project dimension.
        self._update_analytic_distribution("kmitl_project")

    def _reservation_account_domain(self):
        """Budget codes selectable in the reservation picker for this project.

        Mirrors the ``budget_account_id`` field domain: budgetable expense codes
        flagged ``is_project`` whose ``project_type`` matches this project. The
        picker offers only these (other codes still show, but are not selectable),
        and the mixin re-checks the chosen code against this same domain
        server-side in ``apply_reservation_selection`` — so a code outside these
        conditions can be neither picked nor written."""
        self.ensure_one()
        return super()._reservation_account_domain() + [
            ("is_project", "=", True),
            ("project_type", "=", self.project_type),
        ]

    def _reserve_project_commitment(self):
        """Reserve one shared budget.commitment for the project's full
        ``budget_amount`` when its budget is reserved (``to_verify``->``to_send``), drawing from the
        floating project-code pool (ADR-0007). Idempotent: skips when an active
        (non-cancelled) commitment already exists. Blocks on insufficient budget
        unless ``budget.allow_negative`` is set. The project's purchase requests and
        disbursements draw this single commitment down."""
        self.ensure_one()
        if self.budget_commitment_ids.filtered(lambda c: c.state != "cancel"):
            return
        if not self.budget_account_id:
            raise UserError(_("กรุณาระบุรหัสงบประมาณก่อนจองงบประมาณ"))
        if self.budget_amount <= 0:
            raise UserError(_("กรุณาระบุงบประมาณให้มากกว่า 0 ก่อนจองงบประมาณ"))
        analytic_data = {
            "account_id": self.budget_account_id.id,
            "activity_analytic_id": self.activity_analytic_id.id or False,
            "department_analytic_id": self.department_analytic_id.id or False,
            "fund_analytic_id": self.fund_analytic_id.id or False,
            "source_analytic_id": self.source_analytic_id.id or False,
            "kmitl_project_analytic_id": self.analytic_account_id.id or False,
        }
        allow_negative = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("budget.allow_negative", False)
        )
        if not allow_negative:
            self.env["budget.controller"].check_budget_availability(
                analytic_data,
                self.budget_amount,
                self.account_fiscal_year_id.id,
                self.company_id.id,
            )
        dist = dict(self.analytic_distribution or {})
        commitment = self.env["budget.commitment"].create(
            {
                "account_id": self.budget_account_id.id,
                "amount": self.budget_amount,
                "analytic_distribution": dist or False,
                "account_fiscal_year_id": self.account_fiscal_year_id.id,
                "company_id": self.company_id.id,
                "date": fields.Date.context_today(self),
                "ref": self.key or self.name,
                # ชื่อโครงการ = ชื่อใบจอง (shown next to the number wherever a
                # reservation is offered, so it can be told apart from others).
                "title": self.name,
                "description": self.name,
                "kmitl_project_id": self.id,
                "user_id": self.env.user.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "move_type": "reserve",
                            "account_id": self.budget_account_id.id,
                            "analytic_distribution": dist or False,
                            "amount": self.budget_amount,
                            "name": _("Initial reservation"),
                        },
                    )
                ],
            }
        )
        commitment.action_reserve()
        self.message_post(
            body=_("จองงบประมาณ %s จำนวน %s บาท")
            % (commitment.name, "{:,.2f}".format(self.budget_amount))
        )

    def _release_project_commitment(self):
        """Release the reservation when the project leaves the active band
        (reject / cancel / reset to draft). Cancels the commitment only while it is
        untouched and no draw-down has started; once the project is in progress or
        any obligate/consume exists, the commitment is kept and a note is posted so
        in-flight spending is never stranded (ADR-0007)."""
        for project in self:
            in_use = project.state == "in_progress"
            for commitment in project.budget_commitment_ids.filtered(
                lambda c: c.state in ("reserved", "partial")
            ):
                if in_use or commitment.total_obligated or commitment.total_consumed:
                    project.message_post(
                        body=_(
                            "งบประมาณที่จองไว้ (%s) มีการใช้งานแล้ว จึงไม่ยกเลิกการจอง"
                        )
                        % commitment.name
                    )
                    continue
                commitment.action_cancel()
                project.message_post(
                    body=_("ยกเลิกการจองงบประมาณ %s") % commitment.name
                )

    def _resync_project_commitment(self):
        """Re-align the reservation with the current ``budget_amount`` / dimensions
        after the project was edited in ``returned`` (ADR-0005 reopens every field
        there). Safe only pre-approval — no obligate/consume yet — so cancel the
        stale commitment and reserve afresh, which re-runs the availability check
        against the new figures. No-op when nothing budget-relevant changed."""
        self.ensure_one()
        # The plan tables are editable in ``returned`` too, so re-run the same
        # every-line-positive check the reserve step applied.
        self._check_budget_plan_lines()
        active = self.budget_commitment_ids.filtered(
            lambda c: c.state != "cancel"
        )[:1]
        if not active:
            return
        dist = dict(self.analytic_distribution or {})
        if active.amount != self.budget_amount or (
            active.analytic_distribution or {}
        ) != dist:
            self._release_project_commitment()
            self._reserve_project_commitment()

    def _auto_resync_commitment(self):
        """Realign the reservation after the allocated amount changed (budget.move
        post/cancel hook). Safe only while no obligate or consume exists; once
        spending has started the commitment is left alone to avoid stranding
        in-flight draws (ADR-0007)."""
        self.ensure_one()
        active = self.budget_commitment_ids.filtered(lambda c: c.state != "cancel")[:1]
        if not active or active.amount == self.budget_amount:
            return
        if active.total_obligated or active.total_consumed:
            return
        self._release_project_commitment()
        if self.budget_amount > 0:
            self._reserve_project_commitment()

    @api.depends("key")
    def _compute_budget_target_locked(self):
        for rec in self:
            rec.budget_target_locked = bool(rec.key)

    @api.depends("analytic_account_id", "account_fiscal_year_id", "company_id")
    def _compute_budget_amount(self):
        """Current Budget (a) at the project's own dimension: Σ posted
        appropriation/entry balance on budget.move.line where
        kmitl_project_analytic_id == this project's analytic account.
        Reads 0 before allocation (no analytic in draft → 0; no tagged money
        in to_verify before งานแผน transfers → 0)."""
        BML = self.env["budget.move.line"]
        _APPROPRIATION_TYPES = ("appropriation", "entry")
        for rec in self:
            if not rec.analytic_account_id or not rec.account_fiscal_year_id:
                rec.budget_amount = 0.0
                continue
            domain = [
                ("parent_state", "=", "posted"),
                ("move_type", "in", list(_APPROPRIATION_TYPES)),
                ("account_fiscal_year_id", "=", rec.account_fiscal_year_id.id),
                ("company_id", "=", rec.company_id.id),
                ("kmitl_project_analytic_id", "=", rec.analytic_account_id.id),
            ]
            groups = BML.read_group(domain, ["balance"], [])
            rec.budget_amount = (groups[0].get("balance") or 0.0) if groups else 0.0
