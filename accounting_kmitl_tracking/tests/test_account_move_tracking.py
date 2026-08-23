from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestAccountMoveTracking(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        # Build via create() (not Form/init_invoice): the accounting_kmitl form
        # marks the analytic dimensions required, which Form would enforce. This
        # test only exercises draft line/field tracking (never posting).
        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner_a.id,
                "invoice_date": "2026-01-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product_a.id,
                            "quantity": 1,
                            "price_unit": 200.0,
                            "tax_ids": [(6, 0, [])],
                        },
                    )
                ],
            }
        )

    def _flush_tracking(self):
        """tracking_manager posts o2m notes and native tracking at precommit."""
        self.env["base"].flush_model()
        self.env.cr.precommit.run()

    def _bodies(self):
        return [m.body or "" for m in self.invoice.message_ids]

    # ---- configuration is applied by the data file ----

    def test_config_enabled(self):
        self.assertTrue(
            self.env["ir.model"]._get("account.move").active_custom_tracking
        )
        o2m_field = self.env["ir.model.fields"].search(
            [("model", "=", "account.move"), ("name", "=", "invoice_line_ids")],
            limit=1,
        )
        self.assertTrue(o2m_field.custom_tracking)

    # ---- one2many line changes -> consolidated note on the move chatter ----

    def test_line_add_posts_note(self):
        before = len(self.invoice.message_ids)
        self.invoice.write(
            {
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_b.id,
                            "quantity": 1,
                            "price_unit": 100.0,
                            "tax_ids": [(6, 0, [])],
                        },
                    )
                ]
            }
        )
        self._flush_tracking()
        self.assertGreater(len(self.invoice.message_ids), before)
        self.assertTrue(any("New" in b for b in self._bodies()))

    def test_line_update_posts_note(self):
        line = self.invoice.invoice_line_ids[0]
        self.invoice.write(
            {"invoice_line_ids": [(1, line.id, {"price_unit": 999.0})]}
        )
        self._flush_tracking()
        self.assertTrue(any("Change" in b for b in self._bodies()))

    def test_line_unlink_posts_note(self):
        line = self.invoice.invoice_line_ids[0]
        self.invoice.write({"invoice_line_ids": [(2, line.id, 0)]})
        self._flush_tracking()
        self.assertTrue(any("Delete" in b for b in self._bodies()))

    # ---- scalar fields: our data records wire our fields into native tracking ----

    def test_scalar_fields_configured(self):
        # tracking_manager's _track_get_fields returns exactly the custom_tracking
        # set for the active model, so this proves the data records took effect.
        tracked = self.env["account.move"]._track_get_fields()
        for fname in (
            "invoice_date_due",
            "amount_total",
            "amount_residual",
            "journal_id",
            "auto_post",
        ):
            self.assertIn(fname, tracked)

    def test_line_fields_scoped(self):
        # account.move.line is activated so line tracking is bounded rather than
        # the noisy "every writable field" fallback. Our 10 fields must be in the
        # tracked set (core-native line fields may add a few more, e.g.
        # tax_tag_ids / date_maturity — hence issubset, not equality).
        model = self.env["ir.model"]._get("account.move.line")
        self.assertTrue(model.active_custom_tracking)
        tracked = set(
            model.field_id.filtered("custom_tracking").mapped("name")
        )
        expected = {
            "account_id",
            "name",
            "product_id",
            "quantity",
            "price_unit",
            "price_subtotal",
            "debit",
            "credit",
            "tax_ids",
            "analytic_distribution",
        }
        self.assertTrue(expected.issubset(tracked))
