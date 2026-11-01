from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartnerRequiredException(TransactionCase):
    """`purchase_request_approval_excep_partner_required` requires a Vendor on
    ส่งเข้าสารบรรณ for ``direct`` purchases, and skips the check for
    ``advance`` / ``prepaid`` (จ่ายล่วงหน้า) where the Vendor is still unknown
    at submission time.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.rule = env.ref(
            "purchase_request_approval_exception"
            ".purchase_request_approval_excep_partner_required"
        )
        cls.vendor = env["res.partner"].create({"name": "Vendor For PRE-X"})

    def _make_pa(self, payment_type, partner=None):
        pr = self.env["purchase.request"].create(
            {
                "title": "PR for exception test",
                "requested_by": self.env.ref("base.user_admin").id,
            }
        )
        return self.env["purchase.request.approval"].create(
            {
                "request_id": pr.id,
                "title": "PA under test",
                "payment_type": payment_type,
                "partner_id": partner.id if partner else False,
            }
        )

    def _detects(self, pa):
        # base.exception.detect_exceptions returns the ids of rules that fired.
        return self.rule.id in pa.detect_exceptions()

    # --- unit level: the rule method -----------------------------------
    def test_advance_without_partner_passes_rule(self):
        pa = self._make_pa("advance")
        self.assertFalse(pa.purchase_request_approval_check_partner_required())

    def test_prepaid_without_partner_passes_rule(self):
        pa = self._make_pa("prepaid")
        self.assertFalse(pa.purchase_request_approval_check_partner_required())

    def test_direct_without_partner_fails_rule(self):
        pa = self._make_pa("direct")
        self.assertEqual(
            pa.purchase_request_approval_check_partner_required(), pa
        )

    def test_direct_with_partner_passes_rule(self):
        pa = self._make_pa("direct", partner=self.vendor)
        self.assertFalse(pa.purchase_request_approval_check_partner_required())

    # --- integration: detect_exceptions wires the rule in ---------------
    def test_advance_without_partner_no_exception(self):
        self.assertFalse(self._detects(self._make_pa("advance")))

    def test_prepaid_without_partner_no_exception(self):
        self.assertFalse(self._detects(self._make_pa("prepaid")))

    def test_direct_without_partner_raises_exception(self):
        pa = self._make_pa("direct")
        self.assertTrue(self._detects(pa))

    def test_direct_with_partner_no_exception(self):
        pa = self._make_pa("direct", partner=self.vendor)
        self.assertFalse(self._detects(pa))
