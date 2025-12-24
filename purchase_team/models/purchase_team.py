# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PurchaseTeam(models.Model):
    _name = 'purchase.team'
    _description = 'Purchase Team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(
        string='Team Name',
        required=True,
        tracking=True,
        translate=True
    )
    
    active = fields.Boolean(
        default=True,
        tracking=True
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Used to order teams"
    )
    
    description = fields.Text(
        string='Description',
        translate=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Team Leader',
        tracking=True,
    )
    
    member_ids = fields.Many2many(
        'res.users',
        'purchase_team_users_rel',
        'team_id',
        'user_id',
        string='Team Members',
    )
    
    is_membership_multi = fields.Boolean(
        string='Multiple Memberships Allowed',
        compute='_compute_is_membership_multi',
        help='If True, users may belong to several purchase teams. Otherwise membership is limited to a single team.'
    )
    
    filter_domain_pr = fields.Char(
        string='PR Filter Domain'
    )

    filter_domain_pa = fields.Char(
        string='PA Filter Domain'
    )

    filter_domain_po = fields.Char(
        string='PO Filter Domain'
    )

    assign_on_pr = fields.Boolean(
        string='Purchase Request (PR)',
        default=False,
        help='Auto-assign this team for Purchase Requests'
    )
    
    assign_on_pa = fields.Boolean(
        string='Purchase Approval (PA)',
        default=False,
        help='Auto-assign this team for Purchase Approvals'
    )
    
    assign_on_po = fields.Boolean(
        string='Purchase Order (PO)',
        default=False,
        help='Auto-assign this team for Purchase Orders'
    )
    
    member_count = fields.Integer(
        string='Members',
        compute='_compute_member_count',
        store=True
    )

    @api.depends('filter_domain_pr', 'filter_domain_pa', 'filter_domain_po',
                 'assign_on_pr', 'assign_on_pa', 'assign_on_po')
    def _compute_filter_domain_all_json(self):
        for rec in self:
            result = {}
            if rec.assign_on_pr and rec.filter_domain_pr:
                result['purchase.request'] = rec.filter_domain_pr
            if rec.assign_on_pa and rec.filter_domain_pa:
                result['purchase.request.approval'] = rec.filter_domain_pa
            if rec.assign_on_po and rec.filter_domain_po:
                result['purchase.order'] = rec.filter_domain_po
            rec.filter_domain_all_json = str(result)

    def _compute_is_membership_multi(self):
        """Check if multiple team membership is allowed"""
        # This could be configurable via system parameter
        multi = self.env['ir.config_parameter'].sudo().get_param(
            'purchase_team.membership_multi',
            default='True'
        )
        is_multi = multi == 'True'
        for team in self:
            team.is_membership_multi = is_multi

    @api.onchange('user_id')
    def _onchange_user_id_add_to_members(self):
        for team in self:
            if team.user_id:
                if team.user_id not in team.member_ids:
                    team.member_ids = [(4, team.user_id.id)]

    @api.constrains('user_id', 'member_ids')
    def _check_leader_in_members(self):
        """Ensure team leader is in team members"""
        for team in self:
            if team.user_id and team.user_id not in team.member_ids:
                raise ValidationError(_(
                    'Team leader must be a member of the team.'
                ))

    @api.constrains('member_ids')
    def _check_membership_multi(self):
        """Check multiple membership constraint if not allowed"""
        if not self.is_membership_multi:
            for team in self:
                for member in team.member_ids:
                    other_teams = self.search([
                        ('id', '!=', team.id),
                        ('member_ids', 'in', member.id)
                    ])
                    if other_teams:
                        raise ValidationError(_(
                            'User %(user)s already belongs to team %(team)s. '
                            'Multiple team membership is not allowed.',
                            user=member.name,
                            team=other_teams[0].name
                        ))

    def assign_activity_to_team(self, record, summary=None):
        self.ensure_one()
        
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return False
        
        users = self.member_ids
        if not users:
            return False
        
        if not summary:
            summary = _('New %(model)s from %(dept)s', 
                       model=record._description,
                       dept=record.department_id.name if hasattr(record, 'department_id') else '')
        
        activities = self.env['mail.activity']
        for user in users:
            activity = record.activity_schedule(
                activity_type_id=activity_type.id,
                user_id=user.id,
                summary=summary
            )
            activities |= activity
        
        return activities
    
    @api.depends('member_ids')
    def _compute_member_count(self):
        for team in self:
            team.member_count = len(team.member_ids)