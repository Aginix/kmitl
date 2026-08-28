# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

_DR = "disbursement.request"
_SIG = "disbursement.request.signature"
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
    (ADR-0002): every step that acts leaves one row, the row keeps the signer's
    identity as it was at that moment, and a superseded round is archived rather
    than deleted."""

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
            "disbursement.group_disbursement_finance_director",
            job_title="Director of the Finance Division", signature=_PNG_A,
        )
        # Deliberately signature-less: proves an unsigned cell still prints the
        # name and leaves room for a wet signature.
        cls.rector = cls._make_signer(
            "Rector Delegate", "tsb_rector",
            "disbursement.group_disbursement_rector_delegate",
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

    def _sigs(self, dr, step=None, active=True):
        domain = [("request_id", "=", dr.id), ("active", "=", active)]
        if step:
            domain.append(("step", "=", step))
        return self.env[_SIG].with_context(active_test=False).search(domain)

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
        dr.with_user(self.officer).action_validate()
        dr.with_user(self.finance).action_approve_finance()
        with patch(_BUDGET_HOOK):
            dr.with_user(self.rector).action_approve()
        return dr

    # ------------------------------------------------------------------
    # Rows appear as steps are taken
    # ------------------------------------------------------------------
    def test_a_draft_request_has_no_signatures(self):
        """Self-limiting: nothing to print before anything is signed."""
        dr = self._make_signed_dr()
        self.assertFalse(dr.signature_ids)

    def test_validate_stamps_the_verifier_and_a_signature(self):
        dr = self._make_signed_dr()
        dr.with_user(self.officer).action_validate()
        self.assertEqual(dr.verifier_id, self.officer)
        self.assertTrue(dr.verify_date)
        sig = self._sigs(dr, "verify")
        self.assertEqual(len(sig), 1)
        self.assertEqual(sig.signed_by_id, self.officer)
        self.assertEqual(sig.signed_name, "Officer")
        self.assertEqual(sig.signed_position_name, "Finance Analyst")
        self.assertTrue(sig.signed_signature)

    def test_each_step_leaves_one_row_in_flow_order(self):
        dr = self._approve_fully(self._make_signed_dr())
        self.assertEqual(
            dr.signature_ids.mapped("step"),
            ["verify", "finance_approve", "rector_approve"],
        )
        # mapped() on a Many2one dedupes and its order is arbitrary, so walk
        # the rows to assert who signed where.
        self.assertEqual(
            [sig.signed_by_id for sig in dr.signature_ids],
            [self.officer, self.finance, self.rector],
        )

    def test_a_signer_without_an_image_still_gets_a_row(self):
        """The cell prints the name and leaves room for a wet signature."""
        dr = self._approve_fully(self._make_signed_dr())
        sig = self._sigs(dr, "rector_approve")
        self.assertFalse(sig.signed_signature)
        self.assertEqual(sig.signed_name, "Rector Delegate")
        self.assertEqual(sig.signed_position_name, "Vice President for Finance")

    # ------------------------------------------------------------------
    # The snapshot is frozen
    # ------------------------------------------------------------------
    def test_snapshot_is_frozen_against_later_hr_edits(self):
        dr = self._approve_fully(self._make_signed_dr())
        sig = self._sigs(dr, "finance_approve")
        captured = sig.signed_signature

        employee = self.finance.sudo().employee_id
        employee.write({
            "name": "Finance Director (renamed)",
            "job_title": "Moved On",
            "signature": _PNG_B,
        })

        sig.invalidate_recordset()
        self.assertEqual(sig.signed_name, "Finance Director")
        self.assertEqual(
            sig.signed_position_name, "Director of the Finance Division"
        )
        self.assertEqual(sig.signed_signature, captured)

    def test_a_signature_uploaded_after_signing_still_prints(self):
        """The empty-snapshot fallback: signature_image is what the report reads."""
        dr = self._approve_fully(self._make_signed_dr())
        sig = self._sigs(dr, "rector_approve")
        self.assertFalse(sig.signature_image)

        self.rector.sudo().employee_id.signature = _PNG_B
        sig.invalidate_recordset()
        self.assertTrue(sig.signature_image)
        # ...but the snapshot itself stays empty — the freeze is not rewritten.
        self.assertFalse(sig.signed_signature)

    def test_the_snapshot_wins_over_a_replaced_image(self):
        dr = self._approve_fully(self._make_signed_dr())
        sig = self._sigs(dr, "finance_approve")
        captured = sig.signed_signature

        self.finance.sudo().employee_id.signature = _PNG_B
        sig.invalidate_recordset()
        self.assertEqual(sig.signature_image, captured)

    # ------------------------------------------------------------------
    # Superseded rounds are archived, not deleted
    # ------------------------------------------------------------------
    def test_reject_and_re_approve_archives_the_previous_round(self):
        dr = self._make_signed_dr()
        dr.with_user(self.officer).action_validate()
        dr.with_user(self.finance).action_approve_finance()
        dr._action_reject("bad evidence")

        # The approval row only goes when the round actually restarts.
        self.assertTrue(self._sigs(dr, "finance_approve"))
        dr.action_request_approval()
        self.assertFalse(self._sigs(dr, "finance_approve"))
        self.assertEqual(
            len(self._sigs(dr, "finance_approve", active=False)), 1
        )
        # The verification was never redone, so its signature stands.
        self.assertTrue(self._sigs(dr, "verify"))

        dr.with_user(self.finance).action_approve_finance()
        self.assertEqual(len(self._sigs(dr, "finance_approve")), 1)
        self.assertEqual(
            len(self._sigs(dr, "finance_approve", active=False)), 1
        )

    def test_return_to_verification_archives_verify_and_approvals(self):
        dr = self._make_signed_dr()
        dr.with_user(self.officer).action_validate()
        dr.with_user(self.finance).action_approve_finance()
        dr._action_return_to_verification("recheck")

        self.assertEqual(dr.state, "signed")
        self.assertFalse(dr.verifier_id)
        self.assertFalse(dr.verify_date)
        self.assertFalse(dr.signature_ids)
        self.assertEqual(
            len(self.env[_SIG].with_context(active_test=False).search([
                ("request_id", "=", dr.id),
            ])),
            2,
        )

    def test_reset_to_draft_archives_everything(self):
        dr = self._make_signed_dr()
        dr.with_user(self.officer).action_validate()
        dr.with_user(self.finance).action_approve_finance()
        dr.action_cancel()
        dr.action_draft()
        self.assertFalse(dr.verifier_id)
        self.assertFalse(dr.signature_ids)
