from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # โหลดภาษาไทยถ้ายังไม่ถูกโหลด
    if 'th_TH' not in env['res.lang'].search([('code', '=', 'th_TH')]).mapped('code'):
        env['res.lang'].load_lang('th_TH')
    # ตั้งค่าภาษาให้กับผู้ใช้ทุกคน
    users = env['res.users'].search([])
    users.write({'lang': 'th_TH'})
    # ตรวจสอบให้แน่ใจว่า th_TH ถูกเปิดใช้งาน
    env['res.lang']._activate_lang('th_TH')
