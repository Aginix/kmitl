from odoo import api, models, fields


class ResourceAcademicDiscipline(models.Model):
    _name = "resource.academic.discipline"
    _description = "Resource Academic Discipline"
    _rec_name = "name"

    _inherit = ["mail.thread"]

    name = fields.Char(
        string="Discipline Name", required=True, translate=True, tracking=True
    )
    code = fields.Char(tracking=True)

    def name_get(self):
        res = []
        for record in self:
            if record.code:
                res.append((record.id, "%s - %s" % (record.code, record.name)))
            else:
                res.append((record.id, "%s" % (record.name)))
        return res

    @api.model
    def _name_search(
        self, name, args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        args = args or []
        if name:
            args = ["|", ("name", operator, name), ("code", operator, name)] + args
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)
