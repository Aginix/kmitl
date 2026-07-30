# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetCommitment(models.Model):
    _inherit = 'budget.commitment'

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
        help="This operating unit will be defaulted in the move lines.",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    beneficiary_operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="หน่วยงานผู้รับการสนับสนุน",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help=(
            "The unit this reservation is made for (the requester). Its users can "
            "see and draw down this reservation even though it is owned by the "
            "Operating Unit that reserved it. Leave empty for an ordinary "
            "reservation used by the owning unit itself."
        ),
    )

    def _reservation_info_rows(self):
        """Append the owner/beneficiary units to the reservation info widget.

        Who reserved and who may spend is the first thing a beneficiary needs to
        recognise a cross-OU support slip by, so it belongs next to the
        dimensions (ADR-0011). Only shown in multi-OU installations.
        """
        rows = super()._reservation_info_rows()
        if not self.env.user.has_group("operating_unit.group_multi_operating_unit"):
            return rows
        for fname in ("operating_unit_id", "beneficiary_operating_unit_id"):
            value = self[fname]
            rows.append(
                {
                    "label": self._fields[fname]._description_string(self.env),
                    "value": value.display_name if value else "-",
                }
            )
        return rows

    @api.constrains("beneficiary_operating_unit_id", "operating_unit_id")
    def _check_beneficiary_reserve_right(self):
        """Reserving *for another unit* is restricted to central-planning.

        Setting a Beneficiary Unit different from the Owning Unit is the cross-OU
        support act and requires the ``Access all OUs' Budget`` right. An ordinary
        reservation (no beneficiary, or beneficiary equal to the owner) is
        unrestricted, so a plain budget user keeps reserving for its own unit
        without friction (ADR-0011 §Governance). Kept here — alongside the field
        and the visibility-widening record rules, not in the optional
        budget_operating_unit_access_all module — so the gate can never be
        bypassed by installing this module without that one; when that module is
        absent the group does not exist and reserving for another unit is blocked
        outright (safe default).
        """
        if self.env.su:
            return
        group = self.env.ref(
            "budget_operating_unit_access_all.group_all_ou_budget",
            raise_if_not_found=False,
        )
        if group and group in self.env.user.groups_id:
            return
        for rec in self:
            ben = rec.beneficiary_operating_unit_id
            if ben and ben != rec.operating_unit_id:
                raise ValidationError(
                    _(
                        "You may only reserve budget for your own operating unit. "
                        "Reserving for another unit (%s) requires the "
                        "\"Access all OUs' Budget\" right."
                    )
                    % ben.display_name
                )
