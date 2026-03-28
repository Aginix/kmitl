# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def create_invoice_plan(
        self, num_installment, installment_date, interval, interval_type
    ):
        self.ensure_one()

        Decimal = self.env["decimal.precision"]
        prec = Decimal.precision_get("Purchase Invoice Plan Percent")

        accepted_plans = self.invoice_plan_ids.filtered(
            lambda l: l.wa_state == "accept"
        )
        draft_plans = self.invoice_plan_ids.filtered(
            lambda l: l.wa_state != "accept"
        )

        draft_plans.unlink()

        accepted_percent = sum(accepted_plans.mapped("percent"))
        remaining_percent = 100.0 - accepted_percent

        if remaining_percent <= 0:
            return True

        percent = float_round(
            remaining_percent / num_installment,
            prec
        )
        percent_last = remaining_percent - (percent * (num_installment - 1))

        last_installment = max(
            accepted_plans.mapped("installment") or [0]
        )

        invoice_plans = []

        for i in range(num_installment):
            current_percent = (
                percent_last if i == num_installment - 1 else percent
            )

            vals = {
                "installment": last_installment + i + 1,
                "plan_date": installment_date,
                "invoice_type": "installment",
                "percent": current_percent,
            }

            invoice_plans.append((0, 0, vals))

            installment_date = self._next_date(
                installment_date, interval, interval_type
            )

        self.write({
            "invoice_plan_ids": invoice_plans
        })

        return True

