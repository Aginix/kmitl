from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import float_compare, float_is_zero

# Project states a Revision Draft is still open in (ADR-0014).
REVISION_OPEN_STATES = ("draft", "sent", "returned")
# Locked in a Revision Draft: the budget target, the Project Number, the
# project type and the mirrored owners (ADR-0014 decision 2).
REVISION_LOCKED_FIELDS = {
    "budget_account_id",
    "analytic_distribution",
    "analytic_account_id",
    "activity_analytic_id",
    "department_analytic_id",
    "fund_analytic_id",
    "source_analytic_id",
    "account_fiscal_year_id",
    "key",
    "project_type",
    "coordinator_ids",
    "creating_user_id",
    "revision_of_id",
}


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    revision_of_id = fields.Many2one(
        "kmitl.project",
        string="ปรับแผนของโครงการ",
        readonly=True,
        copy=False,
        index=True,
        ondelete="cascade",
        context={"active_test": False},
    )
    revision_ids = fields.One2many(
        "kmitl.project",
        "revision_of_id",
        string="ประวัติปรับแผน",
        context={"active_test": False},
    )
    revision_version = fields.Integer(string="ฉบับที่", readonly=True, copy=False)
    revision_state = fields.Selection(
        [
            ("original", "ฉบับเดิม"),
            ("editing", "กำลังปรับแผน"),
            ("to_approve", "รออนุมัติปรับแผน"),
            ("returned", "ตีกลับแก้ไข"),
            ("approved", "อนุมัติแล้ว"),
            ("rejected", "ไม่อนุมัติ"),
            ("discarded", "ยกเลิก"),
        ],
        string="สถานะการปรับแผน",
        compute="_compute_revision_state",
        store=True,
    )
    revision_reason = fields.Text(string="เหตุผลการปรับแผน", readonly=True, copy=False)
    revision_requested_by_id = fields.Many2one(
        "res.users", string="ผู้ขอปรับแผน", readonly=True, copy=False
    )
    revision_requested_date = fields.Datetime(
        string="วันที่ขอปรับแผน", readonly=True, copy=False
    )
    revision_approved_by_id = fields.Many2one(
        "res.users", string="ผู้อนุมัติปรับแผน", readonly=True, copy=False
    )
    revision_approved_date = fields.Datetime(
        string="วันที่อนุมัติปรับแผน", readonly=True, copy=False
    )
    open_revision_id = fields.Many2one(
        "kmitl.project", compute="_compute_revision_count", string="ร่างปรับแผน"
    )
    revision_count = fields.Integer(compute="_compute_revision_count")
    # A draft has no analytic, so its own budget_amount reads 0: show and
    # check against the live project's.
    revision_live_budget_amount = fields.Float(
        related="revision_of_id.budget_amount",
        string="งบประมาณที่ได้รับการจัดสรร",
        digits="Product Price",
    )
    can_revise = fields.Boolean(compute="_compute_can_revise")

    def init(self):
        super().init()
        self.env.cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS kmitl_project_one_open_revision
            ON kmitl_project (revision_of_id)
            WHERE revision_of_id IS NOT NULL
                AND state IN ('draft', 'sent', 'returned')
            """
        )

    @api.depends("state", "revision_of_id", "revision_version")
    def _compute_revision_state(self):
        mapping = {
            "sent": "to_approve",
            "returned": "returned",
            "complete": "approved",
            "rejected": "rejected",
            "cancel": "discarded",
        }
        for rec in self:
            if not rec.revision_of_id:
                rec.revision_state = False
            elif not rec.revision_version:
                rec.revision_state = "original"
            else:
                rec.revision_state = mapping.get(rec.state, "editing")

    @api.depends("revision_ids.state")
    def _compute_revision_count(self):
        for rec in self:
            revisions = rec.revision_ids
            rec.revision_count = len(revisions)
            rec.open_revision_id = revisions.filtered(
                lambda r: r.state in REVISION_OPEN_STATES
            )[:1]

    @api.depends_context("uid")
    @api.depends("is_project_owner")
    def _compute_can_revise(self):
        is_officer = self.env.user.has_group(
            "kmitl_project.group_kmitl_project_user_all"
        )
        for rec in self:
            rec.can_revise = is_officer or rec.is_project_owner

    # -- guards -----------------------------------------------------------
    def _check_revision_owner(self):
        """Project Owners and project officers create, confirm and discard."""
        if self.env.su:
            return
        if self.filtered(lambda p: not p.can_revise):
            raise AccessError(
                _("เฉพาะเจ้าของโครงการหรือเจ้าหน้าที่โครงการเท่านั้นที่ปรับแผนโครงการได้")
            )

    def _check_revision_manager(self):
        """Only the planning Manager approves or returns a revision."""
        if not self.env.su and not self.env.user.has_group(
            "kmitl_project.group_kmitl_project_manager"
        ):
            raise AccessError(_("เฉพาะเจ้าหน้าที่งานแผน (แอดมิน) เท่านั้นที่อนุมัติการปรับแผนได้"))

    def _check_is_revision(self, states=None):
        for rec in self:
            if not rec.revision_of_id:
                raise UserError(_("ใช้ได้เฉพาะร่างปรับแผนโครงการ"))
            if states and rec.state not in states:
                raise UserError(_("ร่างปรับแผนไม่อยู่ในสถานะที่ทำรายการนี้ได้"))

    def _check_not_revision(self):
        if self.filtered("revision_of_id"):
            raise UserError(_("ร่างปรับแผนโครงการใช้คำสั่งนี้ไม่ได้"))

    @api.model
    def _revision_fields(self):
        """Fields a Revision Draft may change and approval writes back: those
        editable in draft, minus the locked ones (ADR-0014 decision 6)."""
        return [
            name
            for name, field in self._fields.items()
            if field.states
            and "draft" in field.states
            and name not in REVISION_LOCKED_FIELDS
        ]

    @api.model
    def _revision_children(self):
        """``{comodel: inverse_name}`` of the revisable one2many fields."""
        return {
            self._fields[name].comodel_name: self._fields[name].inverse_name
            for name in self._revision_fields()
            if self._fields[name].type == "one2many"
        }

    def _revision_child_records(self, comodel):
        self.ensure_one()
        inverse = self._revision_children()[comodel]
        return (
            self.env[comodel]
            .with_context(active_test=False)
            .search([(inverse, "=", self.id)])
        )

    def _revision_attachments(self):
        """The project's own documents (เอกสารประกอบ), not its chatter's."""
        self.ensure_one()
        attachments = (
            self.env["ir.attachment"]
            .sudo()
            .search([("res_model", "=", self._name), ("res_id", "=", self.id)])
        )
        messages = (
            self.env["mail.message"]
            .sudo()
            .search([("model", "=", self._name), ("res_id", "=", self.id)])
        )
        return attachments - messages.attachment_ids

    # -- write guard ------------------------------------------------------
    def write(self, vals):
        if not self.env.context.get("revision_sync"):
            drafts = self.filtered("revision_of_id")
            if drafts and set(vals) & REVISION_LOCKED_FIELDS:
                raise UserError(
                    _(
                        "ร่างปรับแผนแก้รหัสงบประมาณ มิติ ปีงบประมาณ เลขที่โครงการ "
                        "ประเภทโครงการ หรือผู้ประสานงานไม่ได้"
                    )
                )
            if drafts.filtered(lambda d: d.state not in ("draft", "returned")) and set(
                vals
            ) & set(self._revision_fields()):
                raise UserError(_("แก้ไขร่างปรับแผนได้เฉพาะขณะกำลังปรับแผนหรือถูกตีกลับ"))
        res = super().write(vals)
        if "coordinator_ids" in vals:
            for rec in self.filtered(lambda p: not p.revision_of_id):
                rec.revision_ids.filtered(
                    lambda r: r.state in REVISION_OPEN_STATES
                ).sudo().with_context(revision_sync=True).write(
                    {"coordinator_ids": [(6, 0, rec.coordinator_ids.ids)]}
                )
        return res

    def unlink(self):
        if self.filtered(
            lambda p: (
                p.revision_of_id
                and (p.state in ("complete", "rejected") or not p.revision_version)
            )
        ):
            raise UserError(_("ประวัติการปรับแผนลบไม่ได้"))
        return super().unlink()

    # Base lifecycle actions make no sense on a draft (they would mint a key).
    def action_confirm(self):
        self._check_not_revision()
        return super().action_confirm()

    def action_reserve_budget(self):
        self._check_not_revision()
        return super().action_reserve_budget()

    def action_retry_reserve_budget(self):
        self._check_not_revision()
        return super().action_retry_reserve_budget()

    def action_complete(self):
        self._check_not_revision()
        return super().action_complete()

    def action_draft(self):
        self._check_not_revision()
        return super().action_draft()

    def action_approve(self):
        if self.revision_of_id:
            return self.action_revision_approve()
        return super().action_approve()

    def get_formview_id(self, access_uid=None):
        if len(self) == 1 and self.revision_of_id:
            return self.env.ref(
                "kmitl_project_revision.view_kmitl_project_revision_form"
            ).id
        return super().get_formview_id(access_uid=access_uid)

    # -- create / discard -------------------------------------------------
    def _revision_copy(self, version, default=None):
        """Archived copy of this live project with its revisable children and
        documents; budget lines remember their origin line."""
        self.ensure_one()
        values = {
            "active": False,
            "revision_of_id": self.id,
            "revision_version": version,
            "name": self.name,
            "creating_user_id": self.creating_user_id.id,
            "coordinator_ids": [(6, 0, self.coordinator_ids.ids)],
        }
        values.update(default or {})
        draft = self.copy(values)
        for comodel, inverse in self._revision_children().items():
            for child in self._revision_child_records(comodel):
                child_default = {inverse: draft.id}
                if comodel == "project.budget.line":
                    child_default["origin_line_id"] = child.id
                child.copy(child_default)
        for attachment in self._revision_attachments():
            attachment.copy({"res_id": draft.id})
        return draft

    def action_create_revision(self):
        """ปรับแผนโครงการ: open the project's Revision Draft, creating it."""
        self.ensure_one()
        self._check_not_revision()
        self._check_revision_owner()
        if self.state not in ("in_progress", "complete"):
            raise UserError(_("ปรับแผนได้เฉพาะโครงการที่อนุมัติแล้ว"))
        draft = self.open_revision_id
        if not draft:
            draft = self._revision_copy(self.revision_version + 1)
            self.message_post(
                body=_("สร้างร่างปรับแผนโครงการ ฉบับที่ %s") % draft.revision_version
            )
        return draft._revision_form_action()

    def _revision_form_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ปรับแผนโครงการ"),
            "res_model": "kmitl.project",
            "res_id": self.id,
            "view_mode": "form",
            "views": [
                (
                    self.env.ref(
                        "kmitl_project_revision.view_kmitl_project_revision_form"
                    ).id,
                    "form",
                )
            ],
            "context": {"active_test": False},
            "target": "current",
        }

    def action_revision_discard(self):
        """ยกเลิกร่าง: drop the draft; the live project is untouched."""
        self.ensure_one()
        self._check_is_revision(("draft", "returned"))
        self._check_revision_owner()
        live = self.revision_of_id
        self.unlink()
        return {
            "type": "ir.actions.act_window",
            "res_model": "kmitl.project",
            "res_id": live.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_revisions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ประวัติปรับแผน"),
            "res_model": "kmitl.project",
            "view_mode": "tree,form",
            "views": [
                (
                    self.env.ref(
                        "kmitl_project_revision.view_kmitl_project_revision_tree"
                    ).id,
                    "tree",
                ),
                (
                    self.env.ref(
                        "kmitl_project_revision.view_kmitl_project_revision_form"
                    ).id,
                    "form",
                ),
            ],
            "domain": [("revision_of_id", "=", self.id)],
            "context": {"active_test": False, "create": False},
        }

    def action_open_revision_reason(self):
        """ยืนยัน (owner) or ตีกลับ (Manager): ask for the reason first."""
        self.ensure_one()
        mode = self.env.context.get("revision_mode", "confirm")
        return {
            "type": "ir.actions.act_window",
            "name": _("ยืนยันการปรับแผน") if mode == "confirm" else _("ตีกลับร่างปรับแผน"),
            "res_model": "kmitl.project.revision.reason",
            "view_mode": "form",
            "target": "new",
            "context": {"default_project_id": self.id, "default_mode": mode},
        }

    # -- flow -------------------------------------------------------------
    def action_revision_confirm(self, reason):
        """กำลังปรับแผน/ตีกลับ → รออนุมัติปรับแผน (``sent``)."""
        self.ensure_one()
        self._check_is_revision(("draft", "returned"))
        self._check_revision_owner()
        self.write(
            {
                "revision_reason": reason,
                "revision_requested_by_id": self.env.user.id,
                "revision_requested_date": fields.Datetime.now(),
            }
        )
        self._revision_check()
        self.write({"state": "sent"})
        self.message_post(body=_("ยืนยันการปรับแผน: %s") % reason)

    def action_revision_return(self, reason):
        """ตีกลับ (Manager): back to editable."""
        self.ensure_one()
        self._check_is_revision(("sent",))
        self._check_revision_manager()
        self.write({"state": "returned"})
        self.message_post(body=_("ตีกลับร่างปรับแผน: %s") % reason)

    def action_revision_approve(self):
        """อนุมัติ (Manager): merge the draft onto the live project."""
        self.ensure_one()
        self._check_is_revision(("sent",))
        self._check_revision_manager()
        self._approve_project()

    def _approve_project(self):
        if self.revision_of_id:
            return self._revision_apply()
        return super()._approve_project()

    def _revision_check(self):
        """ADR-0014 decision 3, at ยืนยัน and again at approval."""
        self.ensure_one()
        live = self.revision_of_id
        self._check_budget_plan_lines()
        self._check_budget_plan_total(live.sudo().budget_amount)
        live_lines = (
            self.env["project.budget.line"]
            .sudo()
            .search([("project_id", "=", live.id)])
        )
        claimed = live_lines._get_claimed_amounts()
        kept = {}
        for line in (
            self.env["project.budget.line"]
            .sudo()
            .search([("project_id", "=", self.id), ("origin_line_id", "!=", False)])
        ):
            kept[line.origin_line_id.id] = (
                kept.get(line.origin_line_id.id, 0.0) + line.amount
            )
        rounding = self.company_id.currency_id.rounding
        errors = []
        for line in live_lines:
            amount = claimed.get(line.id, 0.0)
            if float_is_zero(amount, precision_rounding=rounding):
                continue
            if line.id not in kept:
                errors.append(
                    _("ลบ %(name)s ไม่ได้ เนื่องจากเบิกไปแล้ว %(claimed)s บาท")
                    % {"name": line.name, "claimed": "{:,.2f}".format(amount)}
                )
            elif float_compare(kept[line.id], amount, precision_rounding=rounding) < 0:
                errors.append(
                    _("%(name)s ลดได้ไม่ต่ำกว่ายอดเบิกแล้ว %(claimed)s บาท")
                    % {"name": line.name, "claimed": "{:,.2f}".format(amount)}
                )
        if errors:
            raise UserError(
                _("ปรับแผนไม่ได้:\n%s") % "\n".join("- %s" % e for e in errors)
            )
        if self.detect_exceptions():
            raise UserError(
                _("ปรับแผนไม่ได้ เนื่องจาก:\n%s")
                % "\n".join("- %s" % name for name in self.exception_ids.mapped("name"))
            )

    def _revision_expense_diff(self):
        """Html list of the expense-line changes from the live project to this
        draft (old → new)."""
        self.ensure_one()
        Line = self.env["project.budget.line"].sudo()
        live = self.revision_of_id
        old_lines = Line.search(
            [("project_id", "=", live.id), ("budget_type", "=", "expense")]
        )
        new_lines = Line.search(
            [("project_id", "=", self.id), ("budget_type", "=", "expense")]
        )

        def money(value):
            return "{:,.2f}".format(value)

        rows = []
        for line in new_lines:
            old = line.origin_line_id
            if not old:
                rows.append(
                    _("เพิ่ม %(name)s %(new)s บาท")
                    % {"name": line.name, "new": money(line.amount)}
                )
            elif old.name != line.name or old.amount != line.amount:
                rows.append(
                    _("%(old_name)s %(old)s → %(name)s %(new)s บาท")
                    % {
                        "old_name": old.name,
                        "old": money(old.amount),
                        "name": line.name,
                        "new": money(line.amount),
                    }
                )
        for line in old_lines - new_lines.origin_line_id:
            rows.append(
                _("ลบ %(name)s %(old)s บาท")
                % {"name": line.name, "old": money(line.amount)}
            )
        rows.append(
            _("รวมรายจ่าย %(old)s → %(new)s บาท")
            % {
                "old": money(sum(old_lines.mapped("amount"))),
                "new": money(sum(new_lines.mapped("amount"))),
            }
        )
        return Markup("<ul>%s</ul>") % Markup("").join(
            Markup("<li>%s</li>") % escape(row) for row in rows
        )

    def _revision_apply(self):
        """Approval: re-check under lock, snapshot ฉบับที่ 0 on the first
        approval, then merge this draft onto the live project (same id)."""
        self.ensure_one()
        live = self.revision_of_id
        self.env.cr.execute(
            "SELECT id FROM project_budget_line WHERE project_id = %s FOR UPDATE",
            (live.id,),
        )
        self._revision_check()
        if not live.revision_ids.filtered(lambda r: not r.revision_version):
            live._revision_copy(
                0,
                {
                    "state": "complete",
                    "revision_reason": _("ฉบับเดิมก่อนปรับแผนครั้งแรก"),
                },
            )
        diff = self._revision_expense_diff()
        vals = {}
        for name in self._revision_fields():
            field = self._fields[name]
            if field.type != "one2many" and self[name] != live[name]:
                vals[name] = field.convert_to_write(self[name], live)
        if vals:
            live.write(vals)
        self._revision_merge_children()
        self._revision_sync_attachments()
        live.write({"revision_version": self.revision_version})
        self.write(
            {
                "state": "complete",
                "revision_approved_by_id": self.env.user.id,
                "revision_approved_date": fields.Datetime.now(),
            }
        )
        live.message_post(
            body=Markup("%s<br/>%s%s")
            % (
                _("อนุมัติปรับแผนโครงการ ฉบับที่ %s") % self.revision_version,
                _("เหตุผล: %s") % (self.revision_reason or ""),
                diff,
            )
        )

    def _revision_merge_children(self):
        """Budget lines are matched through ``origin_line_id`` and updated in
        place (DR lines keep naming them); other child lines are replaced."""
        self.ensure_one()
        live = self.revision_of_id
        for comodel, inverse in self._revision_children().items():
            old = live._revision_child_records(comodel)
            new = self._revision_child_records(comodel)
            if comodel != "project.budget.line":
                old.unlink()
                for child in new:
                    child.copy({inverse: live.id})
                continue
            for line in new:
                vals = line.copy_data({inverse: live.id})[0]
                if line.origin_line_id in old:
                    vals.pop(inverse)
                    line.origin_line_id.write(vals)
                else:
                    line.origin_line_id = self.env[comodel].create(vals)
            (old - new.origin_line_id).unlink()

    def _revision_sync_attachments(self):
        self.ensure_one()
        live = self.revision_of_id
        old = live._revision_attachments()
        new = self._revision_attachments()
        old.filtered(lambda a: a.checksum not in new.mapped("checksum")).unlink()
        for attachment in new.filtered(
            lambda a: a.checksum not in old.mapped("checksum")
        ):
            attachment.copy({"res_id": live.id})
