# Copyright 2026 Aginix Technologies Co., Ltd. (http://aginix.tech)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Shared setup and assertions for the four bank layouts.

Every bank module renders its file through the same interpreter, so the setup a
layout test needs is the same four times over: a Thai bank carrying the clearing
code the file writes, a journal whose bank account is the one the money leaves
from, payees with Thai names and ten-digit accounts, and posted payments in Baht.
Copying that into four modules is how the four tests drifted apart.

It also defines ``bank_export_format_model``. The KTB, KBANK and BAY suites have
referenced that attribute since they were written, nothing ever defined it --
neither this repository nor upstream's ``CommonBankPaymentExport`` -- so all
three died in ``setUpClass`` and the byte-width assertions they contain have
never run once.
"""

from odoo import fields
from odoo.tools.misc import file_open

from odoo.addons.l10n_th_bank_payment_export.tests.common import CommonBankPaymentExport

# Field kinds for a record spec. Anything else in a spec's third position is a
# literal the field has to equal.
BLANK = "<blank>"
DIGITS = "<digits>"
TEXT = "<text>"


class CommonBankExportFormat(CommonBankPaymentExport):
    """Base for the golden-file tests of every bank layout."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_export_format_model = cls.env["bank.export.format"]
        # The layouts write ``rec.currency_id.name`` and every bank sample says
        # THB, while upstream forces the company to USD by raw SQL. The export
        # and its payments carry THB explicitly rather than the company being
        # rewritten under invoices that were posted in dollars.
        cls.currency_thb = cls.env.ref("base.THB")
        cls.currency_thb.active = True
        cls.country_th = cls.env.ref("base.th")

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def _thai_bank(cls, bic, bank_code, name):
        """Return the bank with this BIC, carrying this clearing code.

        Looked up before it is created because ``account_kmitl`` seeds these
        four, and ``bank_code`` is unique per branch code -- creating a second
        SCB would raise rather than shadow the first.
        """
        bank = cls.env["res.bank"].search([("bic", "=", bic)], limit=1)
        if not bank:
            bank = cls.env["res.bank"].create(
                {"name": name, "bic": bic, "country": cls.country_th.id}
            )
        bank.bank_code = bank_code
        return bank

    @classmethod
    def _paying_journal(cls, bank, acc_number, code):
        """A bank journal whose bank account is the one the file debits.

        The layouts read the sending account off the journal
        (``bank.payment.export.line.sending_acc_number``), so a journal without
        one -- which is what the bank tests used to build -- renders the field
        as zeros and proves nothing.
        """
        company_bank = cls.env["res.partner.bank"].create(
            {
                "acc_number": acc_number,
                "partner_id": cls.env.company.partner_id.id,
                "bank_id": bank.id,
            }
        )
        return cls.env["account.journal"].create(
            {
                "name": "Test %s" % code,
                "code": code,
                "type": "bank",
                "bank_account_id": company_bank.id,
            }
        )

    @classmethod
    def _payee(cls, name, bank, acc_number, title=None):
        """A payee with a Thai name and their account at ``bank``."""
        partner = cls.env["res.partner"].create(
            {
                "name": name,
                "title": title and title.id or False,
                "country_id": cls.country_th.id,
            }
        )
        return cls.env["res.partner.bank"].create(
            {
                "acc_number": acc_number,
                "acc_holder_name": name,
                "partner_id": partner.id,
                "bank_id": bank.id,
            }
        )

    @classmethod
    def _thai_title(cls, shortcut):
        title = cls.env["res.partner.title"].search(
            [("shortcut", "=", shortcut)], limit=1
        )
        return title or cls.env["res.partner.title"].create(
            {"name": shortcut, "shortcut": shortcut}
        )

    @classmethod
    def _posted_payment(cls, journal, partner_bank, amount):
        """A posted outbound manual payment in Baht, ready to be exported."""
        method_line = journal.outbound_payment_method_line_ids.filtered(
            lambda line: line.payment_method_id.code == "manual"
        )[:1]
        payment = cls.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": partner_bank.partner_id.id,
                "partner_bank_id": partner_bank.id,
                "journal_id": journal.id,
                "payment_method_line_id": method_line.id,
                "currency_id": cls.currency_thb.id,
                "amount": amount,
                "date": fields.Date.today(),
            }
        )
        payment.action_post()
        return payment

    @classmethod
    def _export_with_lines(cls, vals, payments):
        """Create a draft export holding exactly these payments, in order.

        Deliberately not ``action_get_all_payments()``: that searches the whole
        database and would sweep in the five payments
        ``CommonBankPaymentExport`` posts in its own setup, so the record order
        -- which every running number and credit sequence in every layout is
        derived from -- would not be the test's to control.
        """
        export = cls.env["bank.payment.export"].create(
            dict(vals, name="/", currency_id=cls.currency_thb.id)
        )
        cls.env["bank.payment.export.line"].create(
            [
                {"payment_export_id": export.id, "payment_id": payment.id}
                for payment in payments
            ]
        )
        return export

    # ------------------------------------------------------------------
    # Reading a rendered file and a fixture the same way
    # ------------------------------------------------------------------
    @classmethod
    def _load_fixture(cls, module, filename):
        """Return the records of a bank's sample file, CRLF stripped.

        Opened as bytes and decoded here rather than as text, because the
        fixture is TIS-620 and a fixed-width record's trailing spaces are part
        of it.
        """
        path = "%s/tests/fixtures/%s" % (module, filename)
        with file_open(path, "rb") as fh:
            content = fh.read()
        return [rec for rec in content.decode("cp874").split("\r\n") if rec]

    @staticmethod
    def _render(export):
        """The file as the interpreter builds it, one record per entry."""
        text = export._export_bank_payment_text_file()
        return text, [rec for rec in text.split("\r\n") if rec]

    # ------------------------------------------------------------------
    # Assertions over a record spec
    # ------------------------------------------------------------------
    @staticmethod
    def _slice(record, spec, wanted):
        """Return the slice of ``record`` the named field occupies."""
        offset = 0
        for name, width, _kind in spec:
            if name == wanted:
                return record[offset : offset + width]
            offset += width
        raise AssertionError("no field %r in this record spec" % wanted)

    def assertRecordShape(self, record, spec, label=""):
        """Check a record against the field table the layout says it has.

        Applied to the bank's own sample as well as to what we render: a
        fixture that stops matching its table is a fixture somebody re-trimmed,
        and that is worth failing on before the comparison that follows it.
        """
        width = sum(field[1] for field in spec)
        self.assertEqual(
            len(record),
            width,
            "%s: record is %s characters, the layout gives it %s\n%r"
            % (label, len(record), width, record),
        )
        offset = 0
        for name, size, kind in spec:
            got = record[offset : offset + size]
            where = "%s: %s at %s-%s" % (label, name, offset + 1, offset + size)
            if kind is BLANK:
                self.assertEqual(
                    got, " " * size, "%s should be empty, is %r" % (where, got)
                )
            elif kind is DIGITS:
                self.assertTrue(
                    got.isdigit(), "%s should be digits, is %r" % (where, got)
                )
            elif kind is TEXT:
                pass
            else:
                self.assertEqual(
                    got, kind, "%s should be %r, is %r" % (where, kind, got)
                )
            offset += size

    def assertRecordMatches(self, produced, expected, spec, variable=(), label=""):
        """Compare a rendered record with the bank's, byte for byte.

        ``variable`` names the fields the sample cannot speak for. Every sample
        KMITL gave us was trimmed down to two or three details out of hundreds,
        so its counts and totals describe a body that is not in the file; and
        the date cannot be reproduced because the export refuses an effective
        date in the past. Both sides are blanked there and the field is checked
        on its own instead.
        """
        self.assertRecordShape(expected, spec, "%s (sample)" % label)
        self.assertRecordShape(produced, spec, "%s (rendered)" % label)
        left, right, offset = produced, expected, 0
        for name, size, _kind in spec:
            if name in variable:
                blank = " " * size
                left = left[:offset] + blank + left[offset + size :]
                right = right[:offset] + blank + right[offset + size :]
            offset += size
        if left != right:
            offset = 0
            for name, size, _kind in spec:
                if left[offset : offset + size] != right[offset : offset + size]:
                    raise AssertionError(
                        "%s: %s at %s-%s is %r, the bank's file has %r"
                        % (
                            label,
                            name,
                            offset + 1,
                            offset + size,
                            left[offset : offset + size],
                            right[offset : offset + size],
                        )
                    )
                offset += size
        self.assertEqual(left, right, label)

    def assertSingleByteEncoding(self, export):
        """The padding is counted in characters; the bank counts bytes.

        They agree only while the layout's encoding is single-byte, which is
        what ``cp874`` is and what the ``utf-8`` default on
        ``bank.export.format.encoding`` is not. A layout that inherits the
        default pads every Thai field three bytes per character wide while every
        character-level assertion still passes.
        """
        text = export._export_bank_payment_text_file()
        content = export._render_bank_payment_file()
        self.assertEqual(
            len(text),
            len(content),
            "%s must use a single-byte encoding, %r is not"
            % (
                export.bank_export_format_id.display_name,
                export.bank_export_format_id.encoding,
            ),
        )
