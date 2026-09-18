# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..models.res_partner import _PARTNER_TYPE_ACCOUNT_FIELDS


@tagged("post_install", "-at_install")
class TestPartnerTypeAccounts(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        def _make_account(code, name, account_type, reconcile=True):
            return cls.env["account.account"].create({
                "name": name,
                "code": code,
                "account_type": account_type,
                "reconcile": reconcile,
                "company_id": cls.company.id,
            })

        cls.recv_a = _make_account("TPTA_REC_A", "Test Recv A", "asset_receivable")
        cls.pay_a = _make_account("TPTA_PAY_A", "Test Payable A", "liability_payable")
        cls.recv_b = _make_account("TPTA_REC_B", "Test Recv B", "asset_receivable")
        cls.pay_b = _make_account("TPTA_PAY_B", "Test Payable B", "liability_payable")

        cls.type_a = cls.env["res.partner.type"].create({
            "name": "Test Type A",
            "company_type": "company",
            "property_account_receivable_id": cls.recv_a.id,
            "property_account_payable_id": cls.pay_a.id,
        })
        cls.type_b = cls.env["res.partner.type"].create({
            "name": "Test Type B",
            "company_type": "company",
            "property_account_receivable_id": cls.recv_b.id,
            "property_account_payable_id": cls.pay_b.id,
        })
        cls.type_bare = cls.env["res.partner.type"].create({
            "name": "Test Type Bare",
            "company_type": "person",
        })
        cls.type_empty = cls.env["res.partner.type"].create({
            "name": "Test Type Empty (no partners)",
            "company_type": "company",
            "property_account_receivable_id": cls.recv_a.id,
            "property_account_payable_id": cls.pay_a.id,
        })
        cls.default_pay = cls.env["ir.property"]._get(
            "property_account_payable_id", "res.partner"
        )

    def _make_partner(self, name, **vals):
        return self.env["res.partner"].create({"name": name, **vals})

    # -------------------------------------------------------------------------
    # create() ORM hook
    # -------------------------------------------------------------------------

    def test_create_stamps_type_accounts(self):
        """create() with an explicit partner_type_id stamps the type's accounts."""
        p = self._make_partner("P1", partner_type_id=self.type_a.id)
        self.assertEqual(p.property_account_receivable_id, self.recv_a)
        self.assertEqual(p.property_account_payable_id, self.pay_a)

    def test_create_explicit_value_wins(self):
        """Caller-supplied payable survives; receivable is still stamped."""
        p = self._make_partner(
            "P2",
            partner_type_id=self.type_a.id,
            property_account_payable_id=self.pay_b.id,
        )
        self.assertEqual(p.property_account_payable_id, self.pay_b)
        self.assertEqual(p.property_account_receivable_id, self.recv_a)

    def test_create_type_without_accounts_keeps_company_default(self):
        """A type with no accounts set never writes False to required fields."""
        p = self._make_partner("P3", partner_type_id=self.type_bare.id)
        self.assertTrue(p.property_account_payable_id)
        self.assertEqual(p.property_account_payable_id, self.default_pay)

    def test_create_batch_writes_once_per_group(self):
        """Batch create: 2 type_a + 1 type_b → 2 write calls on account fields."""
        vals_list = [
            {"name": "Batch A1", "partner_type_id": self.type_a.id},
            {"name": "Batch A2", "partner_type_id": self.type_a.id},
            {"name": "Batch B1", "partner_type_id": self.type_b.id},
        ]
        account_field_writes = []
        _original_write = self.env["res.partner"].__class__.write

        def _tracking_write(self_rec, values):
            if any(f in values for f in _PARTNER_TYPE_ACCOUNT_FIELDS):
                account_field_writes.append(values)
            return _original_write(self_rec, values)

        with patch.object(
            self.env["res.partner"].__class__, "write", _tracking_write
        ):
            self.env["res.partner"].create(vals_list)

        self.assertEqual(len(account_field_writes), 2)

    def test_default_type_accounts_are_stamped(self):
        """partner_type_kmitl defaults a type; accounts from that type are stamped."""
        type_other = self.env.ref("partner_type_kmitl.partner_type_other")
        type_other.property_account_payable_id = self.pay_a.id
        try:
            # No partner_type_id → partner_type_kmitl.create() defaults it
            p = self._make_partner("P4 default")
            self.assertEqual(p.property_account_payable_id, self.pay_a)
        finally:
            type_other.property_account_payable_id = False

    # -------------------------------------------------------------------------
    # write() ORM hook
    # -------------------------------------------------------------------------

    def test_write_type_restamps_mixed_partners(self):
        """write(partner_type_id) re-stamps both partners onto the new type."""
        p1 = self._make_partner("W1", partner_type_id=self.type_a.id)
        p2 = self._make_partner("W2", partner_type_id=self.type_a.id)
        (p1 | p2).write({"partner_type_id": self.type_b.id})
        self.assertEqual(p1.property_account_payable_id, self.pay_b)
        self.assertEqual(p2.property_account_payable_id, self.pay_b)
        self.assertEqual(p1.property_account_receivable_id, self.recv_b)

    def test_write_explicit_value_wins(self):
        """write with both partner_type_id and payable → payable from caller wins."""
        p = self._make_partner("W3", partner_type_id=self.type_a.id)
        p.write({
            "partner_type_id": self.type_b.id,
            "property_account_payable_id": self.pay_a.id,
        })
        self.assertEqual(p.property_account_payable_id, self.pay_a)
        self.assertEqual(p.property_account_receivable_id, self.recv_b)

    def test_write_clearing_type_keeps_accounts(self):
        """write(partner_type_id=False) does not reset accounts to company default."""
        p = self._make_partner("W4", partner_type_id=self.type_a.id)
        self.assertEqual(p.property_account_payable_id, self.pay_a)
        p.write({"partner_type_id": False})
        self.assertEqual(p.property_account_payable_id, self.pay_a)

    # -------------------------------------------------------------------------
    # onchange
    # -------------------------------------------------------------------------

    def test_onchange_sets_accounts(self):
        """_onchange_partner_type_id sets accounts on the NewId record."""
        p = self.env["res.partner"].new({"name": "Onchange P"})
        p.partner_type_id = self.type_a
        p._onchange_partner_type_id()
        self.assertEqual(p.property_account_receivable_id, self.recv_a)
        self.assertEqual(p.property_account_payable_id, self.pay_a)

    # -------------------------------------------------------------------------
    # Apply button
    # -------------------------------------------------------------------------

    def test_type_write_does_not_cascade_then_button_applies(self):
        """Changing a type's account doesn't auto-cascade; button applies it."""
        p = self._make_partner("Button1", partner_type_id=self.type_a.id)
        self.assertEqual(p.property_account_payable_id, self.pay_a)

        # Changing the type's account should NOT auto-cascade
        self.type_a.property_account_payable_id = self.pay_b.id
        try:
            p.invalidate_recordset()
            self.assertEqual(p.property_account_payable_id, self.pay_a)

            result = self.type_a.action_apply_accounts_to_partners()
            self.assertEqual(result["tag"], "display_notification")
            self.assertEqual(result["params"]["type"], "success")
            p.invalidate_recordset()
            self.assertEqual(p.property_account_payable_id, self.pay_b)
        finally:
            self.type_a.property_account_payable_id = self.pay_a.id

    def test_button_includes_archived_partners(self):
        """The Apply button updates archived partners too."""
        p = self._make_partner("Archived1", partner_type_id=self.type_b.id)
        p.write({"active": False})

        self.type_b.property_account_payable_id = self.pay_a.id
        try:
            result = self.type_b.action_apply_accounts_to_partners()
            self.assertEqual(result["params"]["type"], "success")
            p.invalidate_recordset()
            self.assertEqual(p.property_account_payable_id, self.pay_a)
        finally:
            self.type_b.property_account_payable_id = self.pay_b.id
            p.write({"active": True})

    def test_button_second_run_reports_no_change(self):
        """Pressing Apply a second time → warning, 0 updated (idempotency)."""
        p = self._make_partner("Idempotent1", partner_type_id=self.type_a.id)
        # First run stamps
        self.type_a.action_apply_accounts_to_partners()
        # Second run — already correct
        result = self.type_a.action_apply_accounts_to_partners()
        self.assertEqual(result["params"]["type"], "warning")
        self.assertIn("already", result["params"]["message"])
        _ = p  # keep reference

    def test_button_without_accounts_raises(self):
        """Button with no accounts configured raises UserError."""
        with self.assertRaises(UserError):
            self.type_bare.action_apply_accounts_to_partners()

    def test_button_without_partners_warns(self):
        """Button on a type with no partners → warning, no crash."""
        result = self.type_empty.action_apply_accounts_to_partners()
        self.assertEqual(result["tag"], "display_notification")
        self.assertEqual(result["params"]["type"], "warning")
        self.assertIn("No partner", result["params"]["message"])

    # -------------------------------------------------------------------------
    # Drive-by: unlink() archived-partner fix (tested here for coverage)
    # -------------------------------------------------------------------------

    def test_unlink_blocked_when_archived_partner_uses_type(self):
        """unlink() must not allow deleting a type used by an archived partner."""
        type_del = self.env["res.partner.type"].create({
            "name": "To Delete",
            "company_type": "person",
        })
        p = self._make_partner("Archived user", partner_type_id=type_del.id)
        p.write({"active": False})
        with self.assertRaises(UserError):
            type_del.unlink()
        # Clean up
        p.write({"active": True, "partner_type_id": self.type_bare.id})
        type_del.unlink()
