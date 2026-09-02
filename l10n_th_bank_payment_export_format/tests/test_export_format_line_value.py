# Copyright 2026 Aginix Technologies Co., Ltd. (http://aginix.tech)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""What a single field of a bank file is allowed to come out as.

Every byte of every bank file this repository writes goes through
``bank.export.format.line._get_value``, so the width rules belong here rather
than four times over in the bank modules -- and they can be tested without one,
since a format line does not need a bank to render.
"""

from markupsafe import Markup

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestExportFormatLineValue(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.export_format = cls.env["bank.export.format"].create(
            {"name": "Test Layout", "encoding": "cp874"}
        )

    def _field(self, **vals):
        return self.env["bank.export.format.line"].create(
            dict(
                {
                    "bank_id": self.export_format.id,
                    "name": "Test Field",
                    "value_type": "dynamic",
                    "value_alignment": "ljust",
                },
                **vals,
            )
        )

    def test_a_value_that_fits_is_only_padded(self):
        field = self._field(lenght=10, value="'ABC'")
        self.assertEqual(field._get_value({}), "ABC       ")

    def test_the_fill_character_is_used(self):
        field = self._field(
            lenght=6, value_alignment="rjust", value_blank_space="0", value="'42'"
        )
        self.assertEqual(field._get_value({}), "000042")

    def test_left_justified_text_keeps_its_head(self):
        """A payee name is free text the bank's field is too small for.

        SCB gives the receiving bank's name 35 characters and the seeded name
        of Siam Commercial Bank is 39, which used to make the 003 record 359
        characters instead of 355 -- and every field after it unreadable,
        because nothing in a fixed-width file says where a field ends.
        """
        field = self._field(lenght=8, value="'ธนาคารไทยพาณิชย์'")
        self.assertEqual(field._get_value({}), "ธนาคารไท")

    def test_right_justified_figures_keep_their_tail(self):
        """Cutting the head off a figure is what its field overflowing means.

        Keeping the head instead would turn 123456789 satang into 1234, which
        is not a truncated amount but a different one.
        """
        field = self._field(
            lenght=4,
            value_alignment="rjust",
            value_blank_space="0",
            value="'123456789'",
        )
        self.assertEqual(field._get_value({}), "6789")

    def test_a_field_of_no_width_is_left_alone(self):
        """KBANK's Beneficiary Name really is variable-length.

        Its detail records are 123 and 125 characters in the bank's own file,
        because the name is written as it is and the record ends 25 characters
        later. A width of 0 says exactly that, and there is nothing to fit into.
        """
        field = self._field(lenght=0, value="'ปิติ  ทดสอบระบบโอนเงิน'")
        self.assertEqual(field._get_value({}), "ปิติ  ทดสอบระบบโอนเงิน")

    def test_html_is_flattened_before_it_is_fitted(self):
        field = self._field(lenght=5, value="value")
        result = field._get_value({"value": Markup("<p>hello  world</p>")})
        self.assertEqual(result, "hello")

    def test_a_cut_is_logged_with_the_value_in_full(self):
        """A cut figure is a wrong figure, so it has to be findable afterwards."""
        field = self._field(lenght=4, value="'ABCDEFGH'")
        with self.assertLogs(
            "odoo.addons.l10n_th_bank_payment_export_format.models.bank_export_format",
            level="WARNING",
        ) as logged:
            field._get_value({})
        self.assertIn("ABCDEFGH", "\n".join(logged.output))

    def test_an_empty_value_is_still_padded_to_the_width(self):
        field = self._field(lenght=4, value_type="fixed", value=False)
        self.assertEqual(field._get_value({}), "    ")
