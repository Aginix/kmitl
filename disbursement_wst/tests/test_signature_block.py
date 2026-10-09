# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

_DR = "disbursement.request"
_STEP = "disbursement.step"
_BUDGET_HOOK = "odoo.addons.disbursement.models.disbursement_request." \
    "DisbursementRequest._action_approve_budget"

# A 1x1 transparent PNG — enough to prove an image was captured.
_PNG_A = (
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DAwAAA"
    b"BgAB/1i5AAAAAABJRU5ErkJggg=="
)
_PNG_B = (
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADElEQVR42mNk+M8AAAIB"
    b"AQDvvIrKAAAAAElFTkSuQmCC"
)


@tagged("post_install", "-at_install")
class TestSignatureBlock(TransactionCase):
    """The printed signature block is built from frozen per-step snapshots
    (ADR-0002): every signature station that completes leaves one step, the
    step keeps the signer's identity as it was at that moment, and a superseded
    round is archived rather than deleted."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.DR = cls.env[_DR]
        AAA = cls.env["account.analytic.account"]
        cls.dept = AAA.create({
            "name": "Dept",
            "plan_id": cls.env.ref(
                "account_analytic_kmitl.analytic_plan_departments").id,
        })
        cls.source = AAA.create({
            "name": "Gov",
            "plan_id": cls.env.ref(
                "account_analytic_kmitl.analytic_plan_sources").id,
        })
        cls.fund = AAA.create({
            "name": "Fund",
            "plan_id": cls.env.ref(
                "account_analytic_kmitl.analytic_plan_funds").id,
        })
        cls.activity = AAA.create({
            "name": "Act",
            "plan_id": cls.env.ref(
                "account_analytic_kmitl.analytic_plan_activities").id,
        })
        cls.partner = cls.env["res.partner"].create({"name": "Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "Svc", "type": "service"}
        )
        cls.officer = cls._make_signer(
            "Officer", "tsb_officer",
            "disbursement.group_disbursement_officer",
            job_title="Finance Analyst", signature=_PNG_A,
        )
        cls.finance = cls._make_signer(
            "Finance Director", "tsb_finance",
            "disbursement_wst_approve_finance.group_disbursement_finance_director",
            job_title="Director of the Finance Division", signature=_PNG_A,
        )
        # Deliberately signature-less: proves an unsigned cell still prints the
        # name and leaves room for a wet signature.
        cls.rector = cls._make_signer(
            "Rector Delegate", "tsb_rector",
            "disbursement_wst_approve_rector.group_disbursement_rector_delegate",
            job_title="Vice President for Finance",
        )

    @classmethod
    def _make_signer(cls, name, login, group_xmlid, job_title=None,
                     signature=None):
        """A user with the hr.employee the snapshot reads from."""
        user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": name,
            "login": login,
            "groups_id": [(4, cls.env.ref(group_xmlid).id)],
        })
        cls.env["hr.employee"].create({
            "name": name,
            "user_id": user.id,
            "job_title": job_title or "",
            "signature": signature or False,
        })
        return user

    def _sigs(self, dr, station=None):
        """The completed steps of the request."""
        domain = [
            ("request_id", "=", dr.id),
            ("state", "=", "done"),
            ("disposition", "=", "forward"),
        ]
        if station:
            domain.append(("station_code", "=", station))
        return self.env[_STEP].search(domain)

    def _printed(self, dr):
        """What the signature block of the PDF iterates over."""
        dr.invalidate_recordset(["signature_step_ids"])
        return dr.signature_step_ids

    def _act(self, dr, user, note=None):
        return dr.current_step_id.with_user(user).act(note)

    def _make_signed_dr(self):
        dr = self.DR.create({
            "line_ids": [(0, 0, {
                "product_id": self.product.id,
                "name": "line",
                "quantity": 1.0,
                "price_unit": 100.0,
                "partner_id": self.partner.id,
            })],
        })
        dr.analytic_distribution = {
            str(self.dept.id): 100,
            str(self.source.id): 100,
            str(self.fund.id): 100,
            str(self.activity.id): 100,
        }
        dr.action_submit()
        dr.action_sign()
        return dr

    def _approve_fully(self, dr):
        self._act(dr, self.officer)
        self._act(dr, self.finance)
        with patch(_BUDGET_HOOK):
            self._act(dr, self.rector)
        return dr

    # ------------------------------------------------------------------
    # Steps appear as stations are completed
    # ------------------------------------------------------------------
    def test_a_signed_request_has_no_signatures(self):
        """Self-limiting: nothing to print before any station has signed."""
        dr = self._make_signed_dr()
        self.assertFalse(self._printed(dr))

    def test_completing_verify_snapshots_the_verifier(self):
        dr = self._make_signed_dr()
        self._act(dr, self.officer)
        step = self._sigs(dr, "verify")
        self.assertEqual(len(step), 1)
        self.assertEqual(step.acted_by_id, self.officer)
        self.assertTrue(step.acted_date)
        self.assertEqual(step.signed_name, "Officer")
        self.assertEqual(step.signed_position_name, "Finance Analyst")
        self.assertTrue(step.signed_signature)
        self.assertEqual(self._printed(dr), step)

    def test_each_station_leaves_one_step_in_flow_order(self):
        dr = self._approve_fully(self._make_signed_dr())
        printed = self._printed(dr)
        self.assertEqual(
            printed.mapped("station_code"),
            ["verify", "approve_finance", "approve_rector"],
        )
        # mapped() on a Many2one dedupes and its order is arbitrary, so walk
        # the steps to assert who signed where.
        self.assertEqual(
            [step.acted_by_id for step in printed],
            [self.officer, self.finance, self.rector],
        )

    def test_a_signer_without_an_image_still_gets_a_step(self):
        """The cell prints the name and leaves room for a wet signature."""
        dr = self._approve_fully(self._make_signed_dr())
        step = self._sigs(dr, "approve_rector")
        self.assertFalse(step.signed_signature)
        self.assertEqual(step.signed_name, "Rector Delegate")
        self.assertEqual(step.signed_position_name, "Vice President for Finance")

    # ------------------------------------------------------------------
    # The snapshot is frozen
    # ------------------------------------------------------------------
    def test_snapshot_is_frozen_against_later_hr_edits(self):
        dr = self._approve_fully(self._make_signed_dr())
        step = self._sigs(dr, "approve_finance")
        captured = step.signed_signature

        employee = self.finance.sudo().employee_id
        employee.write({
            "name": "Finance Director (renamed)",
            "job_title": "Moved On",
            "signature": _PNG_B,
        })

        step.invalidate_recordset()
        self.assertEqual(step.signed_name, "Finance Director")
        self.assertEqual(
            step.signed_position_name, "Director of the Finance Division"
        )
        self.assertEqual(step.signed_signature, captured)

    def test_a_signature_uploaded_after_signing_still_prints(self):
        """The empty-snapshot fallback: signature_image is what the report reads."""
        dr = self._approve_fully(self._make_signed_dr())
        step = self._sigs(dr, "approve_rector")
        self.assertFalse(step.signature_image)

        self.rector.sudo().employee_id.signature = _PNG_B
        step.invalidate_recordset()
        self.assertTrue(step.signature_image)
        # ...but the snapshot itself stays empty — the freeze is not rewritten.
        self.assertFalse(step.signed_signature)

    def test_the_snapshot_wins_over_a_replaced_image(self):
        dr = self._approve_fully(self._make_signed_dr())
        step = self._sigs(dr, "approve_finance")
        captured = step.signed_signature

        self.finance.sudo().employee_id.signature = _PNG_B
        step.invalidate_recordset()
        self.assertEqual(step.signature_image, captured)

    def test_reset_to_draft_drops_every_step(self):
        """A reset starts the journey over: the steps go, the chatter stays."""
        dr = self._make_signed_dr()
        self._act(dr, self.officer)
        self._act(dr, self.finance)
        dr.action_cancel()
        dr.action_draft()
        self.assertFalse(self._printed(dr))
        self.assertFalse(self._sigs(dr))
