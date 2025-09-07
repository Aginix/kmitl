from odoo import api, fields, models


class AttachmentNameWizard(models.TransientModel):
    _name = 'attachment.name.wizard'
    _description = 'Attachment Name Editor'
    
    attachment_id = fields.Many2one('ir.attachment', string='Attachment', required=True)
    name = fields.Char(string='File Name', required=True)
    description = fields.Text(string='Description')
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'attachment_id' in fields_list and 'default_attachment_id' in self.env.context:
            attachment = self.env['ir.attachment'].browse(self.env.context['default_attachment_id'])
            if attachment.exists():
                res['attachment_id'] = attachment.id
                res['name'] = attachment.name
                res['description'] = attachment.description
        return res
    
    def action_save(self):
        self.ensure_one()
        self.attachment_id.write({
            'name': self.name,
            'description': self.description,
        })
        return {'type': 'ir.actions.act_window_close'}