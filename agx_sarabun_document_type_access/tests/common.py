from odoo.tests.common import new_test_user

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


class TypeReaderCommon(SarabunCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        OU = cls.env["operating.unit"]
        partner = cls.env.company.partner_id
        cls.ou_1 = OU.create(
            {"name": "OU 1", "code": "SBOU1", "partner_id": partner.id}
        )
        cls.ou_2 = OU.create(
            {"name": "OU 2", "code": "SBOU2", "partner_id": partner.id}
        )
        cls.reader_group = cls.env["res.groups"].create({"name": "Sarabun Type Reader"})
        cls.doc_type.reader_group_ids = [(6, 0, cls.reader_group.ids)]
        cls.reader = cls._make_user("sb_reader", cls.ou_1, cls.reader_group)
        cls.reader_other_ou = cls._make_user(
            "sb_reader_ou2", cls.ou_2, cls.reader_group
        )
        cls.non_reader = cls._make_user("sb_non_reader", cls.ou_1)

    @classmethod
    def _make_user(cls, login, ou, *groups):
        user = new_test_user(
            cls.env,
            login=login,
            groups="base.group_user,agx_sarabun.group_sarabun_user",
        )
        user.write(
            {
                "assigned_operating_unit_ids": [(6, 0, ou.ids)],
                "default_operating_unit_id": ou.id,
                "groups_id": [(4, g.id) for g in groups],
            }
        )
        return user

    def _sent_doc(self, ou=None, **vals):
        """A circulating หนังสือ in ``ou`` (default OU 1), routed to user_b."""
        doc = self._make_doc(
            sender=self.user_a, operating_unit_id=(ou or self.ou_1).id, **vals
        )
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        doc.action_send()
        return doc

    def _can_read(self, doc, user):
        return bool(self.Doc.with_user(user).search([("id", "=", doc.id)]))
