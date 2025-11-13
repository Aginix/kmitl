# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import unique

from odoo.addons.base.models import ir_model

select_en = ir_model.select_en


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    def _reflect_fields(self, model_names):
        """ Reflect the fields of the given models. """
        cr = self.env.cr

        for model_name in model_names:
            model = self.env[model_name]
            by_label = {}
            for field in model._fields.values():
                if field.string in by_label:
                    other = by_label[field.string]
                else:
                    by_label[field.string] = field

        # determine expected and existing rows
        rows = []
        for model_name in model_names:
            model_id = self.env['ir.model']._get_id(model_name)
            for field in self.env[model_name]._fields.values():
                rows.append(self._reflect_field_params(field, model_id))
        if not rows:
            return
        cols = list(unique(['model', 'name'] + list(rows[0])))
        expected = [tuple(row[col] for col in cols) for row in rows]

        field_ids = {}
        existing = {}
        for row in select_en(self, ['id'] + cols, "model IN %s", [tuple(model_names)]):
            field_ids[row[1:3]] = row[0]
            existing[row[1:3]] = row[1:]

        # create or update rows
        rows = [row for row in expected if existing.get(row[:2]) != row]
        if rows:
            ids = upsert_en(self, cols, rows, ['model', 'name'])
            for row, id_ in zip(rows, ids):
                field_ids[row[:2]] = id_
            self.pool.post_init(mark_modified, self.browse(ids), cols[2:])

        # update their XML id
        module = self._context.get('module')
        if not module:
            return

        data_list = []
        for (field_model, field_name), field_id in field_ids.items():
            model = self.env[field_model]
            field = model._fields.get(field_name)
            if field and (
                module == model._original_module
                or module in field._modules
                or any(
                    # module introduced field on model by inheritance
                    field_name in self.env[parent]._fields
                    for parent, parent_module in model._inherit_module.items()
                    if module == parent_module
                )
            ):
                xml_id = field_xmlid(module, field_model, field_name)
                record = self.browse(field_id)
                data_list.append({'xml_id': xml_id, 'record': record})
        self.env['ir.model.data']._update_xmlids(data_list)
