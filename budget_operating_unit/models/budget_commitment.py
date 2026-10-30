# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class BudgetCommitment(models.Model):
    _inherit = 'budget.commitment'

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
        help="This operating unit will be defaulted in the move lines.",

    )
    beneficiary_operating_unit_ids = fields.Many2many(
        comodel_name="operating.unit",
        relation="budget_commitment_beneficiary_operating_unit_rel",
        column1="commitment_id",
        column2="operating_unit_id",
        string="หน่วยงานผู้รับการสนับสนุน",
        help=(
            "The units this reservation is made for (the requesters). Their users "
            "can see and draw down this reservation even though it is owned by the "
            "Operating Unit that reserved it. Leave empty for an ordinary "
            "reservation used by the owning unit itself."
        ),
    )
    # Read-only display of the units above: showing the Many2many as tags makes
    # the web client read ``operating.unit`` as the user, and the OU rule hides
    # every unit the user does not hold — so a beneficiary unit opening a slip
    # shared with another unit would hit an AccessError. Computed as sudo.
    beneficiary_operating_unit_names = fields.Char(
        string="หน่วยงานผู้รับการสนับสนุน",
        compute="_compute_beneficiary_operating_unit_names",
        compute_sudo=True,
    )

    @api.depends("beneficiary_operating_unit_ids")
    def _compute_beneficiary_operating_unit_names(self):
        for rec in self:
            rec.beneficiary_operating_unit_names = ", ".join(
                rec.beneficiary_operating_unit_ids.mapped("display_name")
            )

    @api.constrains("beneficiary_operating_unit_ids", "operating_unit_id")
    def _check_beneficiary_reserve_right(self):
        """Reserving *for another unit* is restricted to central-planning.

        Setting a Beneficiary Unit other than the Owning Unit is the cross-OU
        support act and requires the ``Access all OUs' Budget`` right. An ordinary
        reservation (no beneficiary, or only the owner itself) is
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
        # sudo: a plain user cannot read the other units it names, and reading
        # a Many2many checks the comodel's record rules.
        for rec in self.sudo():
            others = rec.beneficiary_operating_unit_ids - rec.operating_unit_id
            if others:
                raise ValidationError(
                    _(
                        "You may only reserve budget for your own operating unit. "
                        "Reserving for another unit (%s) requires the "
                        "\"Access all OUs' Budget\" right."
                    )
                    % ", ".join(others.mapped("display_name"))
                )
