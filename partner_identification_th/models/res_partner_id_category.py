# Copyright 2026 Aginix
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class ResPartnerIdCategory(models.Model):
    _inherit = "res.partner.id_category"

    def validate_res_partner_th_national_id(self, id_number):
        """Validate Thai National ID (13 digits with checksum).

        Algorithm:
        - Multiply digits[0:12] by 13, 12, 11, ..., 2
        - Sum all products
        - Check digit = (11 - (sum % 11)) % 10
        - Compare with digit[12]
        """
        self.ensure_one()
        if not id_number:
            return False

        value = id_number.name
        if not value or len(value) != 13 or not value.isdigit():
            return True

        total = sum(int(value[i]) * (13 - i) for i in range(12))
        check_digit = (11 - (total % 11)) % 10
        if check_digit != int(value[12]):
            return True

        cat = self.env.ref(
            "partner_identification_th.partner_identification_th_national_id_category"
        ).id
        duplicate = self._search_duplicate(cat, id_number, True)
        if duplicate:
            return True

        return False
