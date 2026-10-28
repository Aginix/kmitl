import logging
import re

from lxml import etree, html as lxml_html
from markupsafe import Markup, escape

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

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

    # The states in which the whole form is open for editing: draft authoring
    # and ตีกลับ/ดึงกลับ revision. Used as the per-field ``states=`` override in
    # place of the old draft-only rule.
    EDITABLE_STATES = {
        "draft": [("readonly", False)],
        "to_verify": [("readonly", False)],
        "to_send": [("readonly", False)],
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
        [
            ("project", "โครงการงบประจำ"),
            ("activity", "กิจกรรมงบประจำ"),
            ("strategic_project", "โครงการยุทธศาสตร์"),
        ],
        required=True,
        default="project",
        readonly=True,
        states=EDITABLE_STATES,
    )
    # Html so authors can lay out paragraphs (Tab = .oe-tabs indent). Odoo 16
    # cannot track Html fields, hence no tracking=True.
    introduction = fields.Html(
        string="หลักการและเหตุผล",
        readonly=False,
        states=EDITABLE_STATES,
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
    location = fields.Text(
        string="สถานที่/พื้นที่ดำเนินโครงการ",
        copy=True,
        tracking=True,
        states=EDITABLE_STATES,
    )
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
            ("to_verify", "To Verify"),
            ("to_send", "To Send"),
            ("sent", "Sent"),
            ("returned", "Returned"),
            ("rejected", "Rejected"),
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
        states=EDITABLE_STATES,
    )

    methodology_other = fields.Boolean(
        "อื่น ๆ",
        compute="_compute_methodology_other",
        help="วิธีดำเนินการมีตัวเลือก อื่น ๆ ซึ่งเปิดช่องรายละเอียด",
    )

    methodology_detail = fields.Text(
        "วิธีดำเนินการ (รายละเอียด)",
        copy=True,
        tracking=True,
        readonly=False,
        states=EDITABLE_STATES,
    )

    @api.depends("methodology_ids")
    def _compute_methodology_other(self):
        other = self.env.ref(
            "kmitl_project.methodology_other", raise_if_not_found=False
        )
        for rec in self:
            # In an onchange the lines are NewId records: compare their origin.
            rec.methodology_other = (
                bool(other) and other in rec.methodology_ids._origin
            )

    @api.onchange("methodology_ids")
    def _onchange_methodology_other(self):
        """Drop the detail once อื่น ๆ is unticked, so hidden text never prints."""
        if not self.methodology_other:
            self.methodology_detail = False

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
            self.expense_line_ids if budget_type == "expense" else self.income_line_ids
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
            ids = [int(p) for p in (line.category_parent_path or "").split("/") if p]
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

    budget_account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        index=True,
        tracking=True,
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense'), ('is_project', '=', True)]",
    )

    budget_target_locked = fields.Boolean(
        compute="_compute_budget_target_locked",
        store=True,
    )

    budget_estimate = fields.Float(
        string="งบประมาณโครงการ",
        digits="Product Price",
        tracking=True,
        readonly=True,
        states=EDITABLE_STATES,
        help="งบประมาณโครงการโดยประมาณ ระบุโดยผู้จัดทำโครงการ (เป็นการประมาณการ)",
    )

    budget_amount = fields.Float(
        string="งบประมาณที่ได้รับการจัดสรร",
        digits="Product Price",
        tracking=True,
        compute="_compute_budget_amount",
        store=True,
        readonly=True,
        help="งบประมาณที่ได้รับจัดสรรจริง คำนวณจากยอดโอนเข้า-ออก (budget.move.line) "
        "ที่ตรงกับรหัสงบและมิติทั้งหมดของโครงการ (รวมมิติโครงการ) — "
        "จะ re-sync อัตโนมัติเมื่อแก้รหัสงบ/มิติ",
    )

    budget_reserved = fields.Float(
        string="งบประมาณที่จอง",
        digits="Product Price",
        compute="_compute_budget_reserved",
        help="งบประมาณที่จองไว้จากใบจอง (budget.commitment) ที่ยังไม่ถูกยกเลิก",
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
    # Read from the ledger, which project users cannot read: compute as sudo.
    budget_consumed = fields.Float(
        string="เบิกจ่ายแล้ว",
        digits="Product Price",
        compute="_compute_budget_remaining",
        compute_sudo=True,
        help="ยอดตัดงบ (เบิกจ่าย) ที่ผ่านแล้ว ณ รหัสงบและมิติทั้งหมดของโครงการ",
    )
    budget_remaining = fields.Float(
        string="งบประมาณคงเหลือ",
        digits="Product Price",
        compute="_compute_budget_remaining",
        compute_sudo=True,
        help="งบประมาณที่ได้รับการจัดสรร หักด้วยยอดที่เบิกจ่ายไปแล้ว (เงินที่ยังอยู่ในโครงการ)",
    )

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
        compute_sudo=True,
        tracking=True,
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        # Stored so the project dashboard can search/group by department dimension.
        store=True,
        compute_sudo=True,
        tracking=True,
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
        compute_sudo=True,
        tracking=True,
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        store=False,
        compute_sudo=True,
        tracking=True,
    )

    budget_move_line_count = fields.Integer(
        string="รายการเคลื่อนไหวงบ",
        compute="_compute_budget_move_line_count",
    )
    has_held_money = fields.Boolean(
        string="มีเงินค้างในมิติโครงการ",
        compute="_compute_has_held_money",
        search="_search_has_held_money",
        help="ยังมียอดจัดสรรสุทธิค้างอยู่ในมิติโครงการ (ทุกพิกัด ทุกปีงบประมาณ) "
        "ต้องโอนคืนงบลอยก่อนจึงจะลบโครงการหรือเปลี่ยนรหัสงบ/มิติได้",
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
        """``to_verify`` → open the ยืนยันงบ confirm wizard. On confirm the
        allocated budget is accepted and the project advances to ``to_send``; the
        commitment itself is reserved only when the project is approved
        (``_approve_project``, ADR-0010). Gated: raises if no allocation exists yet."""
        self.ensure_one()
        if self.state != "to_verify":
            raise UserError(_("ยืนยันงบประมาณได้เฉพาะสถานะรอจัดสรรงบประมาณ"))
        if self.budget_amount <= 0:
            raise UserError(
                _(
                    "ยังไม่ได้รับการจัดสรรงบประมาณ "
                    "กรุณาโอนเงิน/เปลี่ยนแปลง/ปรับเพิ่ม-ลดงบประมาณให้เพียงพอก่อน"
                )
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("ยืนยันงบประมาณ"),
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
        self._approve_project()

    def _approve_project(self):
        """Approval → ``in_progress``, reserving the project's budget now that it
        may spend (ADR-0010). A failed reservation never blocks the approval: it
        is rolled back, noted in the chatter, and retried later from
        ``action_retry_reserve_budget``. Legacy projects reserved before approval
        are skipped by the idempotent ``_reserve_project_commitment``."""
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                self._reserve_project_commitment()
        except UserError as e:
            self.message_post(
                body=_("อนุมัติโครงการแล้ว แต่ยังจองงบประมาณไม่ได้: %s") % e.args[0]
            )
        self.write({"state": "in_progress"})

    def action_retry_reserve_budget(self):
        """``in_progress`` without a reservation (the approval-time reserve
        failed) → reserve again; errors surface to the user this time."""
        self.ensure_one()
        if self.state != "in_progress":
            raise UserError(_("จองงบประมาณได้เฉพาะโครงการที่กำลังดำเนินการ"))
        if self.budget_commitment_ids.filtered(lambda c: c.state != "cancel"):
            raise UserError(_("โครงการมีใบจองงบประมาณอยู่แล้ว"))
        self._reserve_project_commitment()

    def action_complete(self):
        """``in_progress`` → ``complete`` (manual; leftover reserved budget is
        returned manually, not auto-released — see ADR-0005)."""
        self.ensure_one()
        if self.state != "in_progress":
            raise UserError(_("ปิดโครงการได้เฉพาะที่กำลังดำเนินการ"))
        open_documents = self._get_open_downstream_documents()
        if open_documents:
            raise UserError(
                _("ไม่สามารถปิดโครงการได้ เนื่องจากยังมีเอกสารค้างดำเนินการ:\n%s")
                % "\n".join("- %s" % doc for doc in open_documents)
            )
        self.write({"state": "complete"})
        self._return_leftover_reservation()

    def _return_leftover_reservation(self):
        """Closing returns what the project reserved but did not spend (คืนจอง,
        ADR-0011) so nothing stays locked; the money itself stays at the
        project's dimension until a Budget User sends it back (โอนคืนงบลอย)."""
        for commitment in self.sudo().budget_commitment_ids.filtered(
            lambda c: c.state in ("reserved", "partial")
        ):
            line = commitment._return_leftover(
                source=self, name=_("คืนเงินเหลือจ่ายเมื่อปิดโครงการ %s") % (self.key or "")
            )
            if line:
                self.message_post(
                    body=_("คืนเงินจองที่เหลือ %s จำนวน %s บาท")
                    % (commitment.name, "{:,.2f}".format(-line.amount))
                )

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
        """Soft delete (ADR-0011): → ``cancel`` and archive the project and its
        analytic account, for a project whose analytic is part of the budget
        history. Only once the project holds no money, has never spent and has
        no open document (``_check_deletable``); reset to draft revives both."""
        for project in self:
            project._check_deletable()
        self._release_project_commitment()
        self.write({"state": "cancel", "active": False})
        self.analytic_account_id.sudo().filtered("active").write({"active": False})

    def _must_soft_delete(self):
        """Whether the project is part of the history and so may only be
        soft-deleted: its analytic has a Ledger Footprint. Extended by bridges
        that keep their own records of the project (e.g. a numbered หนังสือ)."""
        self.ensure_one()
        return self.analytic_account_id._has_ledger_footprint(exclude=self)

    def _check_deletable(self):
        """Every guard of ลบโครงการ (ADR-0011): deleting never moves money and
        never strands a document that still points at the project."""
        self.ensure_one()
        if (
            self.key
            and not self.env.su
            and not self.env.user.has_group(
                "kmitl_project.group_kmitl_project_user_all"
            )
        ):
            raise UserError(
                _("โครงการที่มีเลขที่รันแล้ว (%s) ลบได้เฉพาะเจ้าหน้าที่โครงการเท่านั้น") % self.key
            )
        if self.state == "sent":
            raise UserError(
                _("ไม่สามารถลบโครงการขณะหนังสือกำลังเวียนลงนาม กรุณาดึงกลับหรือยกเลิกการส่งก่อน")
            )
        if self.state == "complete":
            raise UserError(_("ไม่สามารถลบโครงการที่ปิดแล้ว"))
        if self._has_spent():
            raise UserError(
                _("โครงการนี้มีการใช้จ่ายงบประมาณแล้ว ลบไม่ได้ กรุณาคืนเงินเหลือแล้วปิดโครงการแทน")
            )
        reasons = self._get_held_money_reasons()
        if reasons:
            raise UserError(
                _("ไม่สามารถลบโครงการได้ เนื่องจาก:\n%s\nกรุณาโอนคืนงบลอยให้เหลือ 0 บาทก่อน")
                % "\n".join("- %s" % reason for reason in reasons)
            )
        open_documents = self._get_open_downstream_documents()
        if open_documents:
            raise UserError(
                _("ไม่สามารถลบโครงการได้ เนื่องจากยังมีเอกสารที่อ้างถึงโครงการนี้:\n%s")
                % "\n".join("- %s" % doc for doc in open_documents)
            )

    def _get_open_downstream_documents(self):
        """Hook: labels of the documents still open on this project (purchase
        requests, approval requests, disbursements) — extended by the bridges
        that own them. Blocks ปิดโครงการ and ลบโครงการ."""
        self.ensure_one()
        return []

    def _get_project_claims(self):
        """Hook: ``[(label, amount)]`` already claimed on the project's money,
        each of which ``budget_amount`` must keep covering — a Floating Return
        can only take what lies above the largest (ADR-0011). Base: what its
        reservations obligated or consumed; the bridges add the totals their
        own documents are capped by (พ.1, ใบขออนุมัติ, ใบขอเบิก)."""
        self.ensure_one()
        used = sum(
            self.sudo()
            .budget_commitment_ids.filtered(lambda c: c.state != "cancel")
            .mapped("total_obligated")
        )
        return [(_("ผูกพัน/ตัดงบแล้ว"), used)]

    def _has_pending_project_transfer(self):
        """Hook: a transfer into or out of the project's dimension that has not
        posted or been cancelled yet (the budget-transfer bridge)."""
        self.ensure_one()
        return False

    def _project_ledger_sum(self, move_types):
        """Σ posted ``balance`` at the project's dimension over ``move_types``,
        on every coordinate and fiscal year."""
        self.ensure_one()
        if not self.analytic_account_id:
            return 0.0
        groups = (
            self.env["budget.move.line"]
            .sudo()
            .read_group(
                [
                    ("parent_state", "=", "posted"),
                    ("move_type", "in", list(move_types)),
                    ("kmitl_project_analytic_id", "=", self.analytic_account_id.id),
                ],
                ["balance"],
                [],
            )
        )
        return (groups[0].get("balance") or 0.0) if groups else 0.0

    def _has_spent(self):
        """Any net obligated/consumed money at the project's dimension."""
        return not float_is_zero(
            self._project_ledger_sum(("obligate", "consume")), precision_digits=2
        )

    def _held_outside_target(self, account_id, distribution):
        """Σ the net allocation at the project's dimension that sits anywhere but
        the coordinate ``account_id`` + ``distribution``'s budget dimensions —
        e.g. on a target the project was moved away from before ADR-0011."""
        self.ensure_one()
        if not self.analytic_account_id:
            return 0.0
        own = str(self.analytic_account_id.id)
        target = set(distribution or {}) - {own}
        lines = (
            self.env["budget.move.line"]
            .sudo()
            .search(
                [
                    ("parent_state", "=", "posted"),
                    ("move_type", "in", ["appropriation", "entry"]),
                    ("kmitl_project_analytic_id", "=", self.analytic_account_id.id),
                ]
            )
        )
        return sum(
            line.balance
            for line in lines
            if line.account_id.id != account_id
            or set(line.analytic_distribution or {}) - {own} != target
        )

    def _get_held_money_reasons(self, target=None):
        """What makes the project hold money (Held Money, ADR-0011): a net
        allocation on any coordinate/fiscal year — wider than ``budget_amount``,
        which reads only the project's own coordinate — an unspent reservation,
        or a transfer still on its way. Empty when it holds none.

        With ``target`` (``(budget_account_id, analytic_distribution)``) only the
        allocation outside that coordinate counts: retargeting onto where the
        money already sits strands nothing."""
        self.ensure_one()
        reasons = []
        if target:
            held = self._held_outside_target(*target)
        else:
            held = self._project_ledger_sum(("appropriation", "entry"))
        if not float_is_zero(held, precision_digits=2):
            reason = _("มีงบประมาณค้างในมิติโครงการ %s บาท") % "{:,.2f}".format(held)
            if not target:
                # Only the project's own coordinate can be returned from.
                stray = self._held_outside_target(
                    self.budget_account_id.id, self.analytic_distribution
                )
                if not float_is_zero(stray, precision_digits=2):
                    reason += _(
                        " (ในจำนวนนี้ %s บาท อยู่ที่รหัสงบประมาณ/มิติเดิมของโครงการ "
                        "กรุณาแก้รหัสงบประมาณ/มิติกลับให้ตรงกับที่เงินอยู่ก่อนโอนคืนงบลอย)"
                    ) % "{:,.2f}".format(stray)
            reasons.append(reason)
        reserved = sum(
            self.sudo()
            .budget_commitment_ids.filtered(lambda c: c.state != "cancel")
            .mapped("available_to_obligate")
        )
        if not float_is_zero(reserved, precision_digits=2) and reserved > 0:
            reasons.append(
                _("มีเงินจองงบประมาณที่ยังไม่ได้ใช้ %s บาท") % "{:,.2f}".format(reserved)
            )
        if self._has_pending_project_transfer():
            reasons.append(_("มีใบโอนงบประมาณของโครงการที่ยังดำเนินการไม่เสร็จ"))
        return reasons

    def _compute_has_held_money(self):
        held = self._held_analytic_ids(self.analytic_account_id.ids)
        for rec in self:
            rec.has_held_money = rec.analytic_account_id.id in held

    def _search_has_held_money(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise UserError(_("Operation not supported"))
        positive = (operator == "=") == value
        return [
            (
                "analytic_account_id",
                "in" if positive else "not in",
                self._held_analytic_ids(),
            )
        ]

    @api.model
    def _held_analytic_ids(self, analytic_ids=None):
        """Project analytic accounts with a non-zero net posted allocation,
        among ``analytic_ids`` when given."""
        analytic_leaf = (
            ("kmitl_project_analytic_id", "in", analytic_ids)
            if analytic_ids is not None
            else ("kmitl_project_analytic_id", "!=", False)
        )
        groups = (
            self.env["budget.move.line"]
            .sudo()
            .read_group(
                [
                    ("parent_state", "=", "posted"),
                    ("move_type", "in", ["appropriation", "entry"]),
                    analytic_leaf,
                ],
                ["balance"],
                ["kmitl_project_analytic_id"],
            )
        )
        return [
            g["kmitl_project_analytic_id"][0]
            for g in groups
            if not float_is_zero(g["balance"] or 0.0, precision_digits=2)
        ]

    def action_draft(self):
        """Reset to ``draft`` and release the reservation. Blocked from ``sent``
        (handle the หนังสือ first), ``in_progress`` and ``complete`` (no
        un-approving an executing/finished project)."""
        if self.filtered(lambda p: p.state in ("sent", "in_progress", "complete")):
            raise UserError(_("ไม่สามารถกลับเป็นแบบร่างจากสถานะนี้"))
        self._release_project_commitment()
        # A soft-deleted project comes back with its analytic account (ADR-0011).
        self.write({"state": "draft", "active": True})
        self.analytic_account_id.sudo().filtered(lambda a: not a.active).write(
            {"active": True}
        )

    def _check_budget_plan_lines(self):
        """Validate the Project Budget Plan before the budget is reserved. Amounts
        may be left blank/zero while drafting, but every line must carry a positive
        amount before the project confirms its budget (called from the ยืนยันงบ
        wizard, and again from ``_resync_project_commitment``
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
                % "\n".join("- %s" % (line.name or _("(ไม่ระบุรายการ)")) for line in bad)
            )

    def _compute_is_editable(self):
        for rec in self:
            if rec.state in ("draft", "returned"):
                rec.is_editable = True
            else:
                rec.is_editable = False

    def unlink(self):
        """ลบโครงการ (ADR-0011), Odoo's own Delete: a project whose analytic
        has no Ledger Footprint goes for good together with the analytic; one
        that is part of the budget history is soft-deleted (``action_cancel``)
        instead, so it stays archived and can be revived."""
        for rec in self:
            rec._check_deletable()
        soft = self.filtered(lambda p: p._must_soft_delete())
        soft.action_cancel()
        hard = self - soft
        analytics = hard.analytic_account_id
        res = super(KmitlProject, hard).unlink()
        analytics.sudo().unlink()
        return res

    def action_preview_project(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": "/my/kmitl-project/%s" % self.id,
        }

    def _compute_budget_commitment_count(self):
        for rec in self:
            rec.budget_commitment_count = len(rec.budget_commitment_ids)

    def _compute_budget_move_line_count(self):
        BML = self.env["budget.move.line"]
        for rec in self:
            if not rec.analytic_account_id:
                rec.budget_move_line_count = 0
                continue
            rec.budget_move_line_count = BML.search_count(
                [
                    "&",
                    ("kmitl_project_analytic_id", "=", self.analytic_account_id.id),
                    ("account_fiscal_year_id", "=", self.account_fiscal_year_id.id),
                ]
            )

    def action_open_budget_move_lines(self):
        self.ensure_one()
        return {
            "name": _("รายการเคลื่อนไหวงบประมาณ"),
            "type": "ir.actions.act_window",
            "res_model": "budget.move.line",
            "view_mode": "tree,form",
            "domain": [
                "&",
                ("kmitl_project_analytic_id", "=", self.analytic_account_id.id),
                ("account_fiscal_year_id", "=", self.account_fiscal_year_id.id),
            ],
        }

    @api.depends(
        "budget_commitment_ids.amount",
        "budget_commitment_ids.state",
    )
    def _compute_budget_reserved(self):
        """งบประมาณที่จอง = ยอดรวมของใบจอง (budget.commitment) ที่ยังไม่ถูกยกเลิก."""
        for rec in self:
            rec.budget_reserved = sum(
                rec.budget_commitment_ids.filtered(
                    lambda c: c.state != "cancel"
                ).mapped("amount")
            )

    @api.depends("budget_amount")
    def _compute_budget_remaining(self):
        """Money still sitting at the project (ADR-0012) = Project Budget received
        − posted ตัดงบ at the same coordinate ``budget_amount`` sums, so it is
        meaningful in every state and equals the net of the posted Project Budget
        Movements. Not reserved − consumed, and not the budget-account dashboard
        status."""
        BML = self.env["budget.move.line"]
        for rec in self:
            domain = rec._budget_coordinate_domain()
            groups = (
                BML.read_group(
                    domain + [("move_type", "=", "consume")], ["balance"], []
                )
                if domain
                else []
            )
            # Consume lines post a negative balance.
            rec.budget_consumed = -(groups[0].get("balance") or 0.0) if groups else 0.0
            rec.budget_remaining = rec.budget_amount - rec.budget_consumed

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
    def _report_thai_distribute(self, text):
        """Markup for a ``.distribute`` block in the project proposal PDF.

        wkhtmltopdf only stretches justified text at spaces and ignores
        ``text-justify: distribute``, while Thai has no spaces between words.
        So put a space at every Thai word boundary (the CSS cancels its width
        with a negative ``word-spacing``) and wrap the real spaces in
        ``span.rs`` to keep their normal width: justify then spreads each line
        across all its words, and lines wrap between words, never inside one.

        ``text`` is plain text (Text/Char) or Markup (an Html field), in which
        case every text node is segmented and the markup kept as is.
        """
        if not text:
            return ""
        try:
            from pythainlp.tokenize import word_tokenize

            def tokenize(line):
                return word_tokenize(line, engine="newmm", keep_whitespace=True)

        except ImportError:
            _logger.warning("pythainlp is not installed; Thai text not segmented")

            def tokenize(line):
                return [token for token in re.split(r"(\s+)", line) if token]

        def is_thai(char):
            return "\u0e00" <= char <= "\u0e7f" and char not in "ๆฯ"

        def runs(line):
            """Alternating [text, space, text, ...] runs of ``line``, with a
            space inserted at every Thai word boundary inside the text runs."""
            out, prev = [""], ""
            for token in tokenize(line) if line else []:
                if token.isspace():
                    out += [token, ""]
                    prev = ""
                    continue
                if prev and is_thai(prev[-1]) and is_thai(token[0]):
                    out[-1] += " "
                out[-1] += token
                prev = token
            return out

        def real_space(space, tail):
            span = etree.Element("span", {"class": "rs"})
            span.text, span.tail = space, tail
            return span

        if isinstance(text, Markup):
            # The editor puts a zero-width space after each Tab; THSarabunNew
            # has no glyph for it.
            root = lxml_html.fragment_fromstring(
                text.replace("\u200b", ""), create_parent="div"
            )
            for el in list(root.iter(etree.Element)):
                parts = runs(el.text)
                el.text = parts[0]
                for i in range(1, len(parts), 2):
                    el.insert(i // 2, real_space(parts[i], parts[i + 1]))
                if el is not root and el.tail:
                    parts = runs(el.tail)
                    el.tail = parts[0]
                    parent, index = el.getparent(), el.getparent().index(el)
                    for i in range(1, len(parts), 2):
                        parent.insert(
                            index + 1 + i // 2, real_space(parts[i], parts[i + 1])
                        )
            return Markup(lxml_html.tostring(root, encoding="unicode")[5:-6])

        lines = []
        for line in text.split("\n"):
            body = line.lstrip(" \t")
            # The CSS white-space: pre-line collapses leading spaces: keep the
            # line's indent as non-breaking spaces.
            indent = line[: len(line) - len(body)].replace("\t", "    ")
            parts = (
                ["", indent.replace(" ", "\xa0")] + runs(body) if indent else runs(body)
            )
            lines.append(
                Markup("").join(
                    Markup('<span class="rs">%s</span>') % part
                    if i % 2
                    else escape(part)
                    for i, part in enumerate(parts)
                )
            )
        return Markup("\n").join(lines)

    @api.model
    def _create_analytic_account_from_values(self, values):
        # System-minted dimension: project users have no create ACL on analytic
        # accounts, so mint it as superuser (company/OU context is kept).
        return (
            self.env["account.analytic.account"]
            .sudo()
            .create(
                {
                    "name": values.get("name", _("Unknown Analytic Account")),
                    "code": values.get("code"),
                    "company_id": self.env.company.id,
                    "plan_id": self.env.ref(
                        "kmitl_project.analytic_plan_project",
                        raise_if_not_found=True,
                    ).id,
                    # Scope the project's dimension to the project's operating unit so
                    # it stays visible only to the owning unit (analytic OU access rule).
                    "operating_unit_ids": [(6, 0, self.operating_unit_id.ids)]
                    if self.operating_unit_id
                    else False,
                }
            )
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
        # The number's year must come from the ปีงบประมาณ, not today. In the
        # use_date_range path %(year_be)s reads the effective date from the
        # ``ir_sequence_date`` context (the date_range only drives the per-year
        # counter reset), so pin both to the fiscal year's end date — its
        # Gregorian year + 543 is the BE fiscal-year number (e.g. FY 2570 ends
        # 2027 → 2570).
        fiscal_date = self.account_fiscal_year_id.date_to
        self.key = (
            self.env["ir.sequence"]
            .with_context(ir_sequence_date=fiscal_date)
            .next_by_code(
                "kmitl.project",
                sequence_date=fiscal_date,
            )
        )

    # States in which the accounting target (budget code + budget dimensions)
    # may still be edited: while authoring/revising and BEFORE the budget is
    # confirmed (ยืนยันงบ, to_verify→to_send, pins it — the หนังสือ quotes it;
    # the reservation follows at approval, ADR-0010). Only the
    # fiscal year is frozen for good once the running number is minted, because
    # the number encodes the ปีงบ.
    _BUDGET_TARGET_EDITABLE_STATES = ("draft", "to_verify", "returned")

    def write(self, vals):
        """Freeze the **fiscal year** for good once a running number exists — the
        key is stamped with ``account_fiscal_year_id`` and must never drift.

        The rest of the budget target (``budget_account_id`` + the four budget
        dimensions in ``analytic_distribution``) stays editable while the project
        is authored or revised but before its budget is confirmed
        (``_BUDGET_TARGET_EDITABLE_STATES``); once confirmed/sent it is pinned so
        the หนังสือ and the commitment are never left pointing at a stale target.
        Even there it is pinned while the project holds money, which would be
        stranded at the old target (ADR-0011)."""
        if "account_fiscal_year_id" in vals:
            for rec in self:
                if (
                    rec.key
                    and rec.account_fiscal_year_id.id != vals["account_fiscal_year_id"]
                ):
                    raise UserError(
                        _("ไม่สามารถเปลี่ยนปีงบประมาณได้ เนื่องจากโครงการมีเลขที่รันแล้ว (%s)")
                        % rec.key
                    )
        for rec in self:
            if not rec._is_budget_target_change(vals):
                continue
            if rec.state not in self._BUDGET_TARGET_EDITABLE_STATES:
                raise UserError(
                    _(
                        "ไม่สามารถเปลี่ยนรหัสงบประมาณ/มิติงบประมาณได้ เนื่องจากโครงการยืนยันงบประมาณแล้ว (%s)"
                    )
                    % rec.key
                )
            # Money at the old target would be stranded there (ADR-0011).
            reasons = rec._get_held_money_reasons(
                target=(
                    vals.get("budget_account_id", rec.budget_account_id.id),
                    vals["analytic_distribution"]
                    if "analytic_distribution" in vals
                    else rec.analytic_distribution,
                )
            )
            if reasons:
                raise UserError(
                    _(
                        "ไม่สามารถเปลี่ยนรหัสงบประมาณ/มิติงบประมาณได้ เนื่องจาก:\n%s\n"
                        "กรุณาโอนคืนงบลอยก่อน แล้วจึงแก้ไขและจัดสรรงบประมาณใหม่"
                    )
                    % "\n".join("- %s" % reason for reason in reasons)
                )
        res = super().write(vals)
        # Keep the project's analytic account label in step with its name — the
        # name is minted onto the analytic at ส่งเข้าแผน and stays editable in
        # draft/returned, so a later rename must follow through to the dimension.
        if vals.get("name"):
            for rec in self:
                if rec.analytic_account_id and rec.analytic_account_id.name != rec.name:
                    rec.analytic_account_id.sudo().name = rec.name
        return res

    def _is_budget_target_change(self, vals):
        """Whether ``vals`` changes the budget target: the รหัสงบ or any budget
        dimension other than the project's own ``kmitl_project`` key (which is
        folded in when the analytic is minted)."""
        self.ensure_one()
        if (
            "budget_account_id" in vals
            and self.budget_account_id.id != vals["budget_account_id"]
        ):
            return True
        if "analytic_distribution" not in vals:
            return False
        old_dist = self.analytic_distribution or {}
        new_dist = vals["analytic_distribution"] or {}
        proj_key = (
            str(self.analytic_account_id.id) if self.analytic_account_id else None
        )
        return any(
            old_dist.get(k) != new_dist.get(k)
            for k in set(old_dist) | set(new_dist)
            if k != proj_key
        )

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
        ``budget_amount`` when the project is approved (``_approve_project``, ADR-0010), drawing from the
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
        Commitment = self.env["budget.commitment"]
        vals = {
            "account_id": self.budget_account_id.id,
            "amount": self.budget_amount,
            "analytic_distribution": dist or False,
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            "company_id": self.company_id.id,
            "date": fields.Date.context_today(self),
            "ref": self.key or self.name,
            # ชื่อโครงการ = ชื่อใบจอง (shown next to the number wherever a
            # reservation is offered, so it can be told apart from others).
            "title": "[%s] %s" % (self.key, self.name) if self.key else self.name,
            "description": self.name,
            "kmitl_project_id": self.id,
            # Under the หนังสือ callback env.user is the last signer (sudo);
            # the reservation belongs to whoever authored the project.
            "user_id": (self.creating_user_id or self.env.user).id,
        }
        # The reservation's operating unit comes from budget_operating_unit,
        # which this module does not depend on.
        if "operating_unit_id" in Commitment._fields:
            vals["operating_unit_id"] = self.operating_unit_id.id or False
        commitment = Commitment.create(vals)
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
                        body=_("งบประมาณที่จองไว้ (%s) มีการใช้งานแล้ว จึงไม่ยกเลิกการจอง")
                        % commitment.name
                    )
                    continue
                commitment.action_cancel()
                project.message_post(body=_("ยกเลิกการจองงบประมาณ %s") % commitment.name)

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
        active = self.budget_commitment_ids.filtered(lambda c: c.state != "cancel")[:1]
        if not active:
            return
        dist = dict(self.analytic_distribution or {})
        if (
            active.amount != self.budget_amount
            or active.account_id.id != self.budget_account_id.id
            or (active.analytic_distribution or {}) != dist
        ):
            self._release_project_commitment()
            self._reserve_project_commitment()

    @api.depends("key")
    def _compute_budget_target_locked(self):
        for rec in self:
            rec.budget_target_locked = bool(rec.key)

    def _budget_coordinate_domain(self):
        """Posted ``budget.move.line`` at the project's full target coordinate:
        its รหัสงบ + the four base dims + its own ``kmitl_project`` dim, in its
        fiscal year. ``None`` while the coordinate is incomplete."""
        self.ensure_one()
        if (
            not self.analytic_account_id
            or not self.account_fiscal_year_id
            or not self.budget_account_id
        ):
            return None
        return [
            ("parent_state", "=", "posted"),
            ("account_fiscal_year_id", "=", self.account_fiscal_year_id.id),
            ("company_id", "=", self.company_id.id),
            ("account_id", "=", self.budget_account_id.id),
            ("kmitl_project_analytic_id", "=", self.analytic_account_id.id),
            ("department_analytic_id", "=", self.department_analytic_id.id),
            ("fund_analytic_id", "=", self.fund_analytic_id.id),
            ("source_analytic_id", "=", self.source_analytic_id.id),
            ("activity_analytic_id", "=", self.activity_analytic_id.id),
        ]

    @api.depends(
        "analytic_account_id",
        "analytic_distribution",
        "budget_account_id",
        "account_fiscal_year_id",
        "company_id",
    )
    def _compute_budget_amount(self):
        """Current Budget (a) at the project's **full target coordinate**: Σ posted
        appropriation/entry balance on budget.move.line matching the project's
        รหัสงบ (``account_id``) + every budget dimension (the four base dims +
        the project's own ``kmitl_project`` dim). Depending on the target means a
        later edit to the รหัสงบ/มิติ (allowed until จองงบ) re-syncs this figure —
        and it stays consistent with the reserve availability check, which scopes
        to the same coordinate. Reads 0 before allocation (no analytic/รหัสงบ in
        draft → 0; no money tagged at the coordinate in to_verify before งานแผน
        transfers → 0), and drops back to 0 if the target is retargeted away from
        where the allocation actually landed (money stranded at the old coordinate
        → จองงบ correctly blocked until it is re-aligned)."""
        BML = self.env["budget.move.line"]
        for rec in self:
            domain = rec._budget_coordinate_domain()
            if not domain:
                rec.budget_amount = 0.0
                continue
            domain += [("move_type", "in", ["appropriation", "entry"])]
            groups = BML.read_group(domain, ["balance"], [])
            rec.budget_amount = (groups[0].get("balance") or 0.0) if groups else 0.0
