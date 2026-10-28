# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase, tagged

from ..hooks import STATIONS


@tagged("post_install", "-at_install")
class TestStationConfig(TransactionCase):
    def test_stations_are_seated(self):
        admin = self.env.ref("base.user_admin")
        for xmlid, (act_codes, edit_codes) in STATIONS.items():
            station = self.env.ref("disbursement_work_center." + xmlid)
            self.assertCountEqual(station.allowed_act_ids.mapped("code"), act_codes)
            self.assertCountEqual(station.required_act_ids.mapped("code"), act_codes)
            self.assertCountEqual(station.allowed_edit_ids.mapped("code"), edit_codes)
            self.assertIn(admin, station.member_ids)
