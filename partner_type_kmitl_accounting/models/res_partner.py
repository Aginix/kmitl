# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import api, models

_PARTNER_TYPE_ACCOUNT_FIELDS = (
    'property_account_receivable_id',
    'property_account_payable_id',
)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _partner_type_account_vals(self, skip_fields=()):
        """Return write-vals for accounts this partner should inherit from its type.

        Rules:
        - No partner_type_id → empty dict.
        - Fields in skip_fields are left to the caller (explicit value wins).
        - Only propagates a non-empty account on the type (never writes False,
          which would fight the required=True constraint).
        - Skips fields where the partner already holds the same account
          (idempotency; keeps _set_multi off the per-row UPDATE path).

        Note: stamping happens even when the type was *defaulted* rather than
        passed explicitly — required for the vendor case (บริษัท type), and it
        keeps create() consistent with the Apply button. Foot-gun: putting
        accounts on catch-all types (บริษัท / อื่น ๆ) applies them to essentially
        every contact.

        Single-company deployment assumed; no per-company loops. If multi-company
        is ever needed, add a with_company() loop here.
        """
        self.ensure_one()
        if not self.partner_type_id:
            return {}
        vals = {}
        for field in _PARTNER_TYPE_ACCOUNT_FIELDS:
            if field in skip_fields:
                continue
            type_account = self.partner_type_id[field]
            if not type_account:
                continue
            if self[field] == type_account:
                continue
            vals[field] = type_account.id
        return vals

    def _apply_partner_type_accounts(self, skip_fields=()):
        """Stamp partner-type accounts onto self, grouped by resulting vals.

        Returns the records actually changed.

        Early bail-out: if no type in self carries any of the target accounts
        (after honouring skip_fields), avoids the ir.property._get_multi call
        on the partner side — important because create() is a hot path.
        """
        types = self.partner_type_id
        if not any(
            getattr(t, f)
            for t in types
            for f in _PARTNER_TYPE_ACCOUNT_FIELDS
            if f not in skip_fields
        ):
            return self.browse()

        # Group partners by the vals they need written; collapses identical-vals
        # across different types and skips already-correct partners.
        groups = {}
        for partner in self:
            v = partner._partner_type_account_vals(skip_fields=skip_fields)
            if not v:
                continue
            key = tuple(sorted(v.items()))
            if key not in groups:
                groups[key] = (dict(v), self.env['res.partner'])
            groups[key] = (groups[key][0], groups[key][1] | partner)

        changed = self.env['res.partner']
        for vals, partners in groups.values():
            partners.write(vals)
            changed |= partners
        return changed

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Group by the frozenset of account fields explicitly present in the
        # caller's vals — those were set intentionally and must not be overwritten.
        by_skip = defaultdict(list)
        for record, vals in zip(records, vals_list):
            skip = frozenset(f for f in _PARTNER_TYPE_ACCOUNT_FIELDS if f in vals)
            by_skip[skip].append(record.id)
        for skip, ids in by_skip.items():
            self.browse(ids)._apply_partner_type_accounts(skip_fields=skip)
        return records

    def write(self, values):
        res = super().write(values)
        if 'partner_type_id' in values:
            # Account fields present in the same write call were set
            # intentionally by the caller; do not overwrite them.
            # No recursion: the inner write carries only account keys, never
            # partner_type_id.
            # Note: write({'partner_type_id': False}) does not reset accounts
            # back to the company default.
            skip_fields = tuple(f for f in _PARTNER_TYPE_ACCOUNT_FIELDS if f in values)
            self._apply_partner_type_accounts(skip_fields=skip_fields)
        return res

    @api.onchange('partner_type_id')
    def _onchange_partner_type_id(self):
        for partner in self:
            vals = partner._partner_type_account_vals()
            for field, value in vals.items():
                partner[field] = value
