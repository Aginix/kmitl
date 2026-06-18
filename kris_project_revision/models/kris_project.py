# -*- coding: utf-8 -*-
from odoo import _, fields, models


class KrisProject(models.Model):
    _name = "kris.project"
    _inherit = ["kris.project", "base.revision"]

    # --- Revision (base.revision mixin) ---
    current_revision_id = fields.Many2one(
        comodel_name="kris.project",
        string="ฉบับแก้ไขล่าสุด",
        copy=False,
    )
    old_revision_ids = fields.One2many(
        comodel_name="kris.project",
        string="ฉบับแก้ไขก่อนหน้า",
    )
    revision_number = fields.Integer(string="ครั้งที่แก้ไข")
    revision_count = fields.Integer(string="จำนวนฉบับแก้ไข")

    _sql_constraints = [
        (
            "revision_unique",
            "unique(unrevisioned_name, revision_number, company_id)",
            "Project Number and revision must be unique per Company.",
        )
    ]

    # --- Revision (base.revision) ----------------------------------------

    def _get_new_rev_data(self, new_rev_number):
        # Carry the project name onto the new revision so copy() keeps it
        # verbatim instead of appending a "(copy)" suffix; only the Project
        # Number distinguishes revisions (KRIS0001 -> KRIS0001-01).
        vals = super()._get_new_rev_data(new_rev_number)
        vals["project_name"] = self.project_name
        return vals

    def create_revision(self):
        self.ensure_one()
        new = self.copy_revision_with_context()
        self._copy_receipts(new)
        if self.state != "cancel":
            self.action_cancel()
        self.message_post(
            body=_("สร้างฉบับแก้ไขใหม่ %s — ฉบับนี้ถูกเก็บเป็นสำเนาเก่า")
            % new.name
        )
        new.message_post(
            body=_("สร้างจากฉบับเดิม %s (ฉบับแก้ไขครั้งที่ %s)")
            % (self.name, new.revision_number)
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": new.id,
            "target": "current",
        }

    def _copy_receipts(self, new):
        """Carry receipts from the source revision to the new one.

        ``receipt_ids`` is ``copy=False`` on ``kris.project`` so Odoo's
        Duplicate action never drags revenue across. Revision creation is the
        exception: each receipt is copied with its installment and allocation
        cross-links re-pointed at the new revision's records (positional zip,
        same approach as ``_copy_installment_allocations``). Allocation
        breakdowns are rebuilt from scratch so the source's allocation lines
        are not transiently double-counted by
        ``_check_actual_not_exceed_estimated``.
        """
        if not self.receipt_ids:
            return
        inst_map = dict(zip(self.installment_ids, new.installment_ids))
        line_map = dict(zip(self.allocation_line_ids, new.allocation_line_ids))
        Allocation = self.env["kris.project.receipt.allocation"]
        for src_receipt in self.receipt_ids:
            new_inst = inst_map.get(src_receipt.installment_id)
            new_receipt = src_receipt.copy(
                {
                    "project_id": new.id,
                    "installment_id": new_inst.id if new_inst else False,
                    "allocation_ids": False,
                }
            )
            alloc_vals = []
            for src_alloc in src_receipt.allocation_ids:
                new_line = line_map.get(src_alloc.allocation_line_id)
                if not new_line:
                    continue
                alloc_vals.append(
                    {
                        "receipt_id": new_receipt.id,
                        "allocation_line_id": new_line.id,
                        "amount": src_alloc.amount,
                        "remaining_amount": src_alloc.remaining_amount,
                    }
                )
            if alloc_vals:
                Allocation.create(alloc_vals)

    def action_view_revisions(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "kris_project.action_kris_project"
        )
        action["domain"] = ["|", ("active", "=", False), ("active", "=", True)]
        action["context"] = {
            "active_test": 0,
            "search_default_current_revision_id": self.id,
            "default_current_revision_id": self.id,
        }
        return action
