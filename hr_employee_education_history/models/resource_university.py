from odoo import fields, models, api


class ResourceUniversity(models.Model):
    _name = "resource.university"
    _description = "Resource University"

    name = fields.Char(string="University Name", required=True)
    name_th = fields.Char(string="University Name (Thai)")
    country_id = fields.Many2one(
        comodel_name="res.country", string="Country", required=True
    )
    active = fields.Boolean(default=True)

    @api.model
    def _name_search(
        self, name, args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        args = args or []
        if name:
            args = ["|", ("name", operator, name), ("name_th", operator, name)] + args
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

    def name_get(self):
        res = []
        for record in self:
            if record.name_th:
                res.append((record.id, "%s, %s" % (record.name_th, record.name)))
            else:
                res.append((record.id, "%s" % (record.name)))
        return res
