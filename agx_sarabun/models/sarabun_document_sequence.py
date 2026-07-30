# -*- coding: utf-8 -*-
"""The Register (ลงทะเบียน) — atomic, per-เล่มทะเบียน, ปีงบประมาณ-reset numbering.
Replaces the old max()+1 race and the broken fiscal reset (ADR-0002, DESIGN §4).

A ส่วนงาน may keep SEVERAL เล่มทะเบียน (ADR-0011); the หนังสือ picks the book it is
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
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)

    # === Owning unit: a ส่วนงาน may keep several เล่มทะเบียน (ADR-0011) ===
    sender_department_id = fields.Many2one(
        "hr.department", string="ส่วนงาน (Issuing Unit)", required=True, index=True,
        help="หน่วยงานเจ้าของเล่มทะเบียนนี้ — หนึ่งหน่วยงานมีได้หลายเล่มทะเบียน; "
        "หนังสือจะเลือกว่าจะออกเลขจากเล่มใด (ค่าเริ่มต้น = เล่มทะเบียนหลักของหน่วยงาน).",
    )

    # === Rendering ===
    prefix = fields.Char(help="Rendered, not stored on the number (e.g. 'อว 6801.1/').")
    suffix = fields.Char()
    padding = fields.Integer(default=4, help="Zero-pad width of the counter.")
    reset_period = fields.Selection(
        [("fiscal_year", "ปีงบประมาณ (Fiscal Year, Oct–Sep)"),
         ("yearly", "Calendar Year"),
         ("never", "Never")],
        default="fiscal_year",
        required=True,
        help="fiscal_year (ต.ค.–ก.ย.) is the regulation default.",
    )

    number_ids = fields.One2many("sarabun.document.number", "sequence_id", string="Numbers")
    next_counter = fields.Integer(compute="_compute_next_counter", string="Next Number")

    # NOTE: no unique(sender_department_id) — a ส่วนงาน keeps as many เล่มทะเบียน as it
    # needs (ADR-0011); the register books are told apart by their unique ``code``.
    _sql_constraints = [
        ("code_uniq", "unique(code)", "Register code must be unique!"),
    ]

    # ------------------------------------------------------------------ helpers
    def _fiscal_year_for(self, date):
        """ปีงบประมาณ (Oct–Sep). Oct–Dec roll into the next budget year. Returns พ.ศ.

        ``never`` → 0 (single perpetual bucket); ``yearly`` → plain calendar year.
        """
        self.ensure_one()
        if self.reset_period == "never":
            return 0
        by = date.year + 1 if date.month >= 10 else date.year
        if self.reset_period == "yearly":
            by = date.year
        return by + 543  # → พ.ศ.

    @api.depends("number_ids.counter", "number_ids.fiscal_year")
    def _compute_next_counter(self):
        today = fields.Date.context_today(self)
        for seq in self:
            fy = seq._fiscal_year_for(today) if seq.id else 0
            current = seq.number_ids.filtered(lambda n: n.fiscal_year == fy)
            seq.next_counter = (max(current.mapped("counter"), default=0) + 1)

    # ------------------------------------------------------------- allocation
    def allocate(self, document, counter=None, max_retries=3):
        """Atomically register the next official number (DESIGN §4.3).

        Row-locks the register, computes ``MAX(counter)+1`` (per fiscal_year) under
        the lock — or uses the given ``counter`` (manual/gap) — writes the ledger
        row, and relies on ``unique(sequence_id, counter, fiscal_year)`` + a bounded
        retry as the backstop. Replaces the old max()+1 race.
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
                    if counter is None:
                        self.env.cr.execute(
                            "SELECT COALESCE(MAX(counter), 0) + 1 "
                            "FROM sarabun_document_number "
                            "WHERE sequence_id = %s AND fiscal_year = %s",
                            (self.id, fy),
                        )
                        use_counter = self.env.cr.fetchone()[0]
                    else:
                        use_counter = counter
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
                        "Could not allocate a register number (number %s is taken). "
                        "Please try again."
                    ) % (counter if counter is not None else ""))
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
        string="ปีงบประมาณ (พ.ศ.)", required=True, index=True,
        help="Fiscal-year bucket; 0 when the register never resets.",
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

    @api.depends("sequence_id", "counter", "fiscal_year")
    def _compute_register_number(self):
        for n in self:
            seq = n.sequence_id
            counter = str(n.counter).zfill(seq.padding or 1)
            fy = ("/%s" % n.fiscal_year) if n.fiscal_year else ""
            n.register_number = f"{seq.prefix or ''}{counter}{seq.suffix or ''}{fy}"
