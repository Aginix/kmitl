# -*- coding: utf-8 -*-
"""The Register (ลงทะเบียน) — atomic, per-เล่มทะเบียน, calendar-year-reset numbering.
Replaces the old max()+1 race and the broken year reset (ADR-0002, DESIGN §4).

A ส่วนงาน may keep SEVERAL เล่มทะเบียน (ADR-0012); the หนังสือ picks the book it is
issued from (defaulting to the unit's เล่มทะเบียนหลัก).
"""
import logging

import psycopg2

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SarabunDocumentSequence(models.Model):
    _name = "sarabun.document.sequence"
    _description = "Sarabun Register (เล่มทะเบียนหนังสือ)"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    # === Owning unit: a ส่วนงาน may keep several เล่มทะเบียน (ADR-0012) ===
    sender_department_id = fields.Many2one(
        "hr.department", string="ส่วนงาน (Issuing Unit)", index=True,
        help="หน่วยงานเจ้าของเล่มทะเบียนนี้ — หนึ่งหน่วยงานมีได้หลายเล่มทะเบียน; "
        "หนังสือจะเลือกว่าจะออกเลขจากเล่มใด (ค่าเริ่มต้น = เล่มทะเบียนหลักของหน่วยงาน).",
    )

    # === Rendering ===
    prefix = fields.Char(help="Rendered, not stored on the number (e.g. 'อว 6801.1/').")
    suffix = fields.Char()
    padding = fields.Integer(default=4, help="Zero-pad width of the counter.")

    number_ids = fields.One2many("sarabun.document.number", "sequence_id", string="Numbers")
    next_counter = fields.Integer(compute="_compute_next_counter", string="Next Number")

    # NOTE: no unique constraint — a ส่วนงาน keeps as many เล่มทะเบียน as it needs
    # (ADR-0012) and books are identified by ส่วนงาน + ชื่อเล่ม. The old required,
    # institute-unique ``code`` was dropped: nothing resolved or rendered from it,
    # so it only forced the admin to invent a unique string per book.

    @api.returns("self", lambda value: value.id)
    def copy(self, default=None):
        """Suffix the duplicate's ชื่อเล่ม. Two books of one ส่วนงาน are told apart by
        their name alone, so a plain copy would be indistinguishable in the list."""
        self.ensure_one()
        default = dict(default or {})
        default.setdefault("name", _("%s (สำเนา)") % (self.name or ""))
        return super().copy(default)

    # ------------------------------------------------------------------ helpers
    def _fiscal_year_for(self, date):
        """The counter's year bucket (พ.ศ.) — resets each calendar year.

        Named ``_fiscal_year_for`` for continuity; the register now always resets
        on the calendar year, so the month is irrelevant.
        """
        self.ensure_one()
        return date.year + 543  # → พ.ศ.

    @api.depends("number_ids.counter", "number_ids.fiscal_year")
    def _compute_next_counter(self):
        today = fields.Date.context_today(self)
        for seq in self:
            fy = seq._fiscal_year_for(today) if seq.id else 0
            current = seq.number_ids.filtered(lambda n: n.fiscal_year == fy)
            seq.next_counter = (max(current.mapped("counter"), default=0) + 1)

    # ------------------------------------------------------------- allocation
    def allocate(self, document, max_retries=3):
        """Atomically register the next official number (DESIGN §4.3).

        Row-locks the register, computes ``MAX(counter)+1`` (per fiscal_year) under
        the lock, writes the ledger row, and relies on
        ``unique(sequence_id, counter, fiscal_year)`` + a bounded retry as the
        backstop. Replaces the old max()+1 race.
        """
        self.ensure_one()
        fy = self._fiscal_year_for(fields.Date.context_today(self))
        Number = self.env["sarabun.document.number"]
        for attempt in range(max_retries):
            try:
                with self.env.cr.savepoint():
                    self.env.cr.execute(
                        "SELECT id FROM sarabun_document_sequence WHERE id = %s FOR UPDATE",
                        (self.id,),
                    )
                    self.env.cr.execute(
                        "SELECT COALESCE(MAX(counter), 0) + 1 "
                        "FROM sarabun_document_number "
                        "WHERE sequence_id = %s AND fiscal_year = %s",
                        (self.id, fy),
                    )
                    use_counter = self.env.cr.fetchone()[0]
                    number = Number.create({
                        "sequence_id": self.id,
                        "counter": use_counter,
                        "fiscal_year": fy,
                        "state": "used",
                        "document_id": document.id,
                        "used_date": fields.Datetime.now(),
                    })
                    number.flush_recordset()  # force INSERT so a collision raises here
                return number
            except psycopg2.IntegrityError:
                if attempt + 1 == max_retries:
                    raise UserError(_(
                        "Could not allocate a register number. Please try again."
                    ))
                continue


class SarabunDocumentNumber(models.Model):
    _name = "sarabun.document.number"
    _description = "Sarabun Register Number (ledger)"
    _order = "fiscal_year desc, counter desc"
    _rec_name = "register_number"

    sequence_id = fields.Many2one(
        "sarabun.document.sequence", required=True, index=True, ondelete="cascade",
    )
    counter = fields.Integer(required=True, index=True, help="Running integer, scoped per fiscal_year.")
    fiscal_year = fields.Integer(
        string="ปี (พ.ศ.)", required=True, index=True,
        help="Calendar-year bucket (พ.ศ.); the counter resets each January.",
    )
    state = fields.Selection(
        [("reserved", "Reserved"), ("used", "Used"), ("voided", "Voided (ยกเลิก)")],
        default="used", required=True, index=True,
    )
    document_id = fields.Many2one(
        "sarabun.document", string="Document", ondelete="restrict",
        help="A used number must keep its document link for audit.",
    )
    register_number = fields.Char(compute="_compute_register_number", store=True)
    used_date = fields.Datetime()

    # reserve mode (manual compose — phase-2 UX)
    reserved_by_id = fields.Many2one("res.users")
    reserved_date = fields.Datetime()
    note = fields.Text()

    # voiding (§4.7)
    void_reason = fields.Selection([("rejected", "Rejected"), ("cancelled", "Cancelled")])
    void_date = fields.Datetime()

    _sql_constraints = [
        ("counter_fy_seq_uniq", "unique(sequence_id, counter, fiscal_year)",
         "A register number must be unique per register per fiscal year!"),
    ]

    @api.depends("sequence_id", "counter")
    def _compute_register_number(self):
        # เลขที่หนังสือไม่มีเลขปี (feedback): the running number renders prefix + counter
        # + suffix only. The ปีงบ still buckets and resets the counter (the fiscal_year
        # field + unique(sequence_id, counter, fiscal_year) constraint) but is no longer
        # printed in the number itself — the ลงวันที่ on the หนังสือ carries the year.
        for n in self:
            seq = n.sequence_id
            counter = str(n.counter).zfill(seq.padding or 1)
            n.register_number = f"{seq.prefix or ''}{counter}{seq.suffix or ''}"
