# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression


class SarabunRouteTemplate(models.Model):
    _inherit = "sarabun.route.template"

    owner_id = fields.Many2one(
        "res.users",
        string="เจ้าของ (Owner)",
        default=lambda self: self.env.user,
        copy=False,
        index=True,
    )
    visibility = fields.Selection(
        [
            ("personal", "ส่วนตัว (Personal)"),
            ("unit", "ทั้งหน่วยงาน (Unit)"),
            ("public", "ทุกคน (Public)"),
        ],
        string="การมองเห็น (Visibility)",
        default=lambda self: self._default_visibility(),
        required=True,
        index=True,
    )
    # Mirrors the write ir.rule (manager, or owner) so the form can render
    # fields readonly for users who only see the template via public/unit
    # visibility — surfaces the "no edit" state upfront instead of failing at
    # save time with AccessError.
    can_edit = fields.Boolean(compute="_compute_can_edit")
    # Virtual per-user partition used as a synthetic group-by in the search
    # view. Not stored — resolved through _search_mine_bucket for domain use
    # and through the read_group override for grouping.
    mine_bucket = fields.Selection(
        [("mine", "แม่แบบของฉัน"), ("others", "แม่แบบของคนอื่น")],
        string="ของฉัน / ของคนอื่น",
        compute="_compute_mine_bucket",
        search="_search_mine_bucket",
        store=False,
    )

    @api.depends("owner_id")
    @api.depends_context("uid")
    def _compute_can_edit(self):
        is_manager = self.env.user.has_group("agx_sarabun.group_sarabun_manager")
        uid = self.env.user.id
        for record in self:
            record.can_edit = is_manager or record.owner_id.id == uid

    @api.depends("owner_id")
    @api.depends_context("uid")
    def _compute_mine_bucket(self):
        uid = self.env.user.id
        for record in self:
            record.mine_bucket = "mine" if record.owner_id.id == uid else "others"

    def _search_mine_bucket(self, operator, value):
        uid = self.env.user.id
        # Normalise to a set of {'mine','others'} keys the caller is asking for.
        if operator in ("=", "!="):
            keys = {value} if operator == "=" else {"mine", "others"} - {value}
        elif operator in ("in", "not in"):
            wanted = set(value or [])
            keys = wanted if operator == "in" else {"mine", "others"} - wanted
        else:
            return expression.FALSE_DOMAIN
        keys &= {"mine", "others"}
        if keys == {"mine", "others"}:
            return expression.TRUE_DOMAIN
        if not keys:
            return expression.FALSE_DOMAIN
        return [("owner_id", "=" if keys == {"mine"} else "!=", uid)]

    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        gb_list = [groupby] if isinstance(groupby, str) else list(groupby)
        # Only intercept when mine_bucket is the top-level partition — the UI
        # never puts it deeper. Everything else must delegate untouched.
        if not gb_list or gb_list[0] != "mine_bucket":
            return super().read_group(
                domain, fields, groupby,
                offset=offset, limit=limit, orderby=orderby, lazy=lazy,
            )
        # Defensive: aggregates against mine_bucket make no sense (Selection),
        # and would propagate the field name into the SQL projection.
        sub_fields = [f for f in fields if not f.split(":")[0].startswith("mine_bucket")]
        rest = gb_list[1:]
        uid = self.env.user.id
        buckets = [
            ("mine", [("owner_id", "=", uid)]),
            ("others", [("owner_id", "!=", uid)]),
        ]
        # Mirror base ORM count-key convention (models.py:2347-2351): lazy AND
        # multiple groupbys → '<first_gb>_count', else '_count'.
        count_key = "mine_bucket_count" if (lazy and len(gb_list) >= 2) else "_count"

        result = []
        for bucket_key, bucket_dom in buckets:
            sub = super().read_group(
                domain=expression.AND([domain, bucket_dom]) if domain else bucket_dom,
                fields=sub_fields,
                groupby=rest,
                offset=0, limit=None,
                orderby=orderby, lazy=lazy,
            )
            if not rest:
                row = sub[0] if sub else {count_key: 0}
                row["mine_bucket"] = bucket_key
                row["__domain"] = (
                    expression.AND([domain, bucket_dom]) if domain else bucket_dom
                )
                result.append(row)
            else:
                for row in sub:
                    row["mine_bucket"] = bucket_key
                    row["__domain"] = expression.AND([row["__domain"], bucket_dom])
                    result.append(row)

        if offset:
            result = result[offset:]
        if limit is not None:
            result = result[:limit]
        return result

    def _default_visibility(self):
        if self.env.su or self.env.user.has_group(
            "agx_sarabun.group_sarabun_manager"
        ):
            return "public"
        return "personal"

    @api.constrains("visibility")
    def _check_visibility_public(self):
        if self.env.su:
            return
        for template in self:
            if template.visibility == "public" and not self.env.user.has_group(
                "agx_sarabun.group_sarabun_manager"
            ):
                raise ValidationError(
                    "เฉพาะผู้จัดการสารบรรณเท่านั้นที่สามารถตั้งค่าการมองเห็น"
                    "เป็น 'ทุกคน (Public)' ได้"
                )

    @api.constrains("visibility", "department_id")
    def _check_visibility_unit_department(self):
        for template in self:
            if template.visibility == "unit" and not template.department_id:
                raise ValidationError(
                    "กรุณาระบุหน่วยงานเมื่อเลือกการมองเห็นแบบ "
                    "'ทั้งหน่วยงาน (Unit)'"
                )
