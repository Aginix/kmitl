# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBankExportFormatFollowsBank(TransactionCase):
    """The layout has to follow the bank the file is going to.

    Lives in the KTB module rather than in ``l10n_th_bank_payment_export_format``
    because ``bank`` is an empty Selection there — the bank modules are what fill
    it — so the format module cannot create a format to test against on its own.

    KTB is also the useful case: it is the one bank shipping two layouts, so it
    exercises both branches (nothing to pick vs. exactly one to pick).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Export = cls.env["bank.payment.export"]
        cls.ktb_formats = cls.env["bank.export.format"].search(
            [("bank", "=", "KRTHTHBK")]
        )

    def test_01_two_layouts_are_not_guessed(self):
        """KTB ships iPay and Direct Credit H/D/T; neither may be picked for the
        officer."""
        self.assertEqual(
            len(self.ktb_formats), 2, "KTB is expected to ship exactly two layouts"
        )
        export = self.Export.new({})
        export.bank = "KRTHTHBK"
        export._onchange_bank_export_format_id()
        self.assertFalse(export.bank_export_format_id)

    def test_02_a_single_layout_is_selected(self):
        """Every bank but KTB has one layout, and then there is nothing to ask.

        Simulated by dropping one of KTB's two inside the test transaction, so the
        assertion does not depend on which other bank modules are installed.
        """
        self.ktb_formats[1].unlink()
        export = self.Export.new({})
        export.bank = "KRTHTHBK"
        export._onchange_bank_export_format_id()
        self.assertEqual(export.bank_export_format_id, self.ktb_formats[0])

    def test_03_a_layout_of_another_bank_is_dropped(self):
        """The bug this guards: the domain filters the dropdown, never the value
        already in it, so the previous bank's layout used to stay behind and the
        file went out written in it."""
        export = self.Export.new(
            {"bank": "KRTHTHBK", "bank_export_format_id": self.ktb_formats[0].id}
        )
        export.bank = False
        export._onchange_bank_export_format_id()
        self.assertFalse(export.bank_export_format_id)

    def test_04_a_mismatch_cannot_be_saved(self):
        """The onchange only guards the form; an export assembled in code has to
        be refused outright."""
        with self.assertRaises(UserError):
            self.Export.create(
                {"name": "/", "bank_export_format_id": self.ktb_formats[0].id}
            )
