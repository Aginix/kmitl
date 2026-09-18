# -*- coding: utf-8 -*-
from odoo import _, api, models


class SelectWorkAcceptanceInvoicePlanWizard(models.TransientModel):
    _inherit = "select.work.acceptance.invoice.plan.wizard"

    @api.depends("installment_id")
    def _compute_active_installment_ids(self):
        super()._compute_active_installment_ids()
        for rec in self:
            rec.active_installment_ids = rec.active_installment_ids.filtered(
                lambda l: not l.child_ids
            )

    @api.onchange("installment_id")
    def _onchange_installment_id(self):
        if not self.installment_id:
            return
        active = self.active_installment_ids
        if not active:
            return
        min_key = min(
            (l.installment, l.sub_installment) for l in active
        )
        cur_key = (self.installment_id.installment, self.installment_id.sub_installment)
        if cur_key > min_key:
            return {
                "warning": {
                    "title": _("Installment Warning:"),
                    "message": _(
                        "The 1st installment is %(min_install)s "
                        "but you are choosing %(cur_install)s"
                    )
                    % {
                        "min_install": (
                            "%s.%s" % min_key if min_key[1] else "%s" % min_key[0]
                        ),
                        "cur_install": (
                            "%s.%s" % cur_key if cur_key[1] else "%s" % cur_key[0]
                        ),
                    },
                }
            }
