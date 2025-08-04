# -*- coding: utf-8 -*-
import logging
from datetime import date, datetime
from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetDemo(models.AbstractModel):
    _name = 'budget.demo'
    _description = 'Budget Demo Data Generator'

    @api.model
    def generate_demo_data(self):
        """Generate comprehensive budget move demo data"""
        _logger.info("Starting budget demo data generation...")
        
        try:
            # Check if demo data already exists
            if self._demo_data_exists():
                _logger.info("Budget demo data already exists, skipping generation")
                return
            
            # Generate demo budget moves
            moves = self._create_demo_budget_moves()
            
            _logger.info(f"Successfully created {len(moves)} demo budget moves")
            return moves
            
        except Exception as e:
            _logger.error(f"Failed to generate budget demo data: {str(e)}")
            # Don't raise exception to avoid breaking module installation
            return False

    @api.model
    def regenerate_demo_data(self):
        """Force regeneration of demo data (useful for upgrades)"""
        _logger.info("Force regenerating budget demo data...")
        
        try:
            # Remove existing demo data first
            self.remove_demo_data()
            
            # Generate fresh demo data
            moves = self._create_demo_budget_moves()
            
            _logger.info(f"Successfully regenerated {len(moves)} demo budget moves")
            return moves
            
        except Exception as e:
            _logger.error(f"Failed to regenerate budget demo data: {str(e)}")
            return False

    def _demo_data_exists(self):
        """Check if demo data already exists"""
        demo_moves = self.env['budget.move'].search([
            ('name', 'like', 'DEMO_%'),
            ('move_type', '=', 'appropriation'),
            ('is_initial_appropriation', '=', True)
        ])
        
        # Check if we have the expected demo moves
        expected_moves = [
            'DEMO_DEPT02_APPROPRIATION_2568',
            'DEMO_DEPT03_REVENUE_2568', 
            'DEMO_MULTI_ACTIVITY_2568',
            'DEMO_CSV_DEPT02_COMPREHENSIVE_2568',
            'DEMO_CSV_DEPT03_REVENUE_2568'
        ]
        
        existing_names = demo_moves.mapped('name')
        missing_moves = [name for name in expected_moves if name not in existing_names]
        
        if missing_moves:
            _logger.info(f"Missing demo moves detected: {missing_moves}")
            # Remove partial demo data to ensure clean regeneration
            if demo_moves:
                _logger.info("Removing partial demo data for clean regeneration")
                try:
                    # Cancel posted moves first
                    posted_moves = demo_moves.filtered(lambda m: m.state == 'posted')
                    if posted_moves:
                        posted_moves.button_cancel()
                    # Delete existing partial data
                    demo_moves.unlink()
                except Exception as e:
                    _logger.warning(f"Could not remove partial demo data: {str(e)}")
            return False
        
        _logger.info(f"All expected demo moves exist: {existing_names}")
        return True

    def _create_demo_budget_moves(self):
        """Create comprehensive demo budget moves with appropriation type"""
        moves = []
        
        # Get required reference data
        refs = self._get_reference_data()
        if not refs:
            _logger.warning("Required reference data not found, skipping demo creation")
            return []
        
        # Create Department 02 Appropriation Move (Large Engineering Faculty Budget)
        dept02_move = self._create_dept02_budget_move(refs)
        if dept02_move:
            moves.append(dept02_move)
        
        # Create Department 03 Appropriation Move (Revenue Budget)
        dept03_move = self._create_dept03_budget_move(refs)
        if dept03_move:
            moves.append(dept03_move)
        
        # Create additional demonstration moves
        multi_activity_move = self._create_multi_activity_budget_move(refs)
        if multi_activity_move:
            moves.append(multi_activity_move)
        
        # Create comprehensive budget moves (same as CSV data)
        csv_based_moves = self._create_csv_based_budget_moves(refs)
        if csv_based_moves:
            moves.extend(csv_based_moves)
        
        return moves

    def _get_reference_data(self):
        """Get all required reference data for demo creation"""
        try:
            # Get fiscal year
            fiscal_year = self.env.ref('kmitl_demo.account_fiscal_year_y2568', raise_if_not_found=False)
            if not fiscal_year:
                _logger.warning("Fiscal year y2568 not found")
                return None
            
            # Get departments
            dept_02 = self.env.ref('account_analytic_kmitl.dept_02', raise_if_not_found=False)
            dept_01 = self.env.ref('account_analytic_kmitl.dept_01', raise_if_not_found=False)
            
            # Get sources
            source_2 = self.env.ref('account_analytic_kmitl.source_2', raise_if_not_found=False)
            
            # Get journals
            expense_journal = self.env.ref('budget.budget_move_expense_journal', raise_if_not_found=False)
            revenue_journal = self.env.ref('budget.budget_move_revenue_journal', raise_if_not_found=False)
            
            # Get some budget accounts
            budget_accounts = self._get_sample_budget_accounts()
            
            # Get analytic accounts (activities, funds)
            analytics = self._get_sample_analytics()
            
            if not all([fiscal_year, dept_02, source_2, expense_journal, budget_accounts, analytics]):
                missing = []
                if not fiscal_year: missing.append('fiscal_year')
                if not dept_02: missing.append('dept_02')
                if not source_2: missing.append('source_2')
                if not expense_journal: missing.append('expense_journal')
                if not budget_accounts: missing.append('budget_accounts')
                if not analytics: missing.append('analytics')
                _logger.warning(f"Missing required references: {missing}")
                return None
            
            return {
                'fiscal_year': fiscal_year,
                'dept_02': dept_02,
                'dept_01': dept_01,
                'source_2': source_2,
                'expense_journal': expense_journal,
                'revenue_journal': revenue_journal,
                'budget_accounts': budget_accounts,
                'analytics': analytics,
            }
        except Exception as e:
            _logger.error(f"Error getting reference data: {str(e)}")
            return None

    def _get_sample_budget_accounts(self):
        """Get sample budget accounts for demo data"""
        account_refs = [
            'budget.budget_account_5101010038',  # Personnel - Base salary
            'budget.budget_account_5101010004',  # Personnel - Benefits
            'budget.budget_account_5101020045',  # Operating - Utilities
            'budget.budget_account_5104010203',  # Equipment - IT
            'budget.budget_account_5107010500',  # Travel - Academic
            'budget.budget_account_5108000020',  # Special activities
        ]
        
        accounts = {}
        for ref in account_refs:
            account = self.env.ref(ref, raise_if_not_found=False)
            if account:
                key = ref.split('.')[-1]  # Get last part as key
                accounts[key] = account
        
        return accounts if accounts else None

    def _get_sample_analytics(self):
        """Get sample analytic accounts for demo data"""
        analytic_refs = {
            'activities': [
                'account_analytic_kmitl.activity_09007010110',  # General administration
                'account_analytic_kmitl.activity_09007010111',  # Academic support
                'account_analytic_kmitl.activity_090100201',   # Education
            ],
            'funds': [
                'account_analytic_kmitl.fund_0100',  # General fund
                'account_analytic_kmitl.fund_0200',  # Special fund
                'account_analytic_kmitl.fund_0600',  # Development fund
            ]
        }
        
        analytics = {'activities': {}, 'funds': {}}
        
        for category, refs in analytic_refs.items():
            for ref in refs:
                analytic = self.env.ref(ref, raise_if_not_found=False)
                if analytic:
                    key = ref.split('.')[-1]  # Get last part as key
                    analytics[category][key] = analytic
        
        return analytics if analytics['activities'] and analytics['funds'] else None

    def _create_dept02_budget_move(self, refs):
        """Create Department 02 comprehensive budget appropriation move"""
        try:
            move_vals = {
                'name': 'DEMO_DEPT02_APPROPRIATION_2568',
                'move_type': 'appropriation',
                'is_initial_appropriation': True,
                'is_initial_appropriation': True,
                'date': date(2024, 10, 1),
                'date_range_fy_id': refs['fiscal_year'].id,
                'department_analytic_id': refs['dept_02'].id,
                'source_analytic_id': refs['source_2'].id,
                'journal_id': refs['expense_journal'].id,
                'ref': 'Demo: Engineering Faculty Budget Appropriation FY2568',
                'state': 'draft',
            }
            
            # Create budget lines with 4D analytics
            lines = []
            
            # Personnel costs
            if 'budget_account_5101010038' in refs['budget_accounts']:
                lines.extend(self._create_personnel_lines(refs))
            
            # Operating expenses
            if 'budget_account_5101020045' in refs['budget_accounts']:
                lines.extend(self._create_operating_lines(refs))
            
            # Equipment purchases
            if 'budget_account_5104010203' in refs['budget_accounts']:
                lines.extend(self._create_equipment_lines(refs))
            
            # Travel and training
            if 'budget_account_5107010500' in refs['budget_accounts']:
                lines.extend(self._create_travel_lines(refs))
            
            # Special activities
            if 'budget_account_5108000020' in refs['budget_accounts']:
                lines.extend(self._create_special_activity_lines(refs))
            
            move_vals['line_ids'] = [(0, 0, line) for line in lines]
            
            # Create the move
            move = self.env['budget.move'].create(move_vals)
            _logger.info(f"Created demo budget move: {move.name}")
            
            return move
            
        except Exception as e:
            _logger.error(f"Failed to create dept02 budget move: {str(e)}")
            return None

    def _create_personnel_lines(self, refs):
        """Create personnel cost budget lines"""
        lines = []
        analytics = refs['analytics']
        accounts = refs['budget_accounts']
        
        # Base salary line
        if 'budget_account_5101010038' in accounts and 'activity_09007010110' in analytics['activities']:
            lines.append({
                'account_id': accounts['budget_account_5101010038'].id,
                'activity_analytic_id': analytics['activities']['activity_09007010110'].id,
                'department_analytic_id': refs['dept_02'].id,
                'fund_analytic_id': analytics['funds']['fund_0100'].id,
                'source_analytic_id': refs['source_2'].id,
                'balance': 5000000.0,
                'name': 'Demo: Base salary allocation',
            })
        
        # Benefits line
        if 'budget_account_5101010004' in accounts and 'activity_09007010110' in analytics['activities']:
            lines.append({
                'account_id': accounts['budget_account_5101010004'].id,
                'activity_analytic_id': analytics['activities']['activity_09007010110'].id,
                'department_analytic_id': refs['dept_02'].id,
                'fund_analytic_id': analytics['funds']['fund_0100'].id,
                'source_analytic_id': refs['source_2'].id,
                'balance': 1500000.0,
                'name': 'Demo: Employee benefits allocation',
            })
        
        return lines

    def _create_operating_lines(self, refs):
        """Create operating expense budget lines"""
        lines = []
        analytics = refs['analytics']
        accounts = refs['budget_accounts']
        
        if 'budget_account_5101020045' in accounts and 'activity_09007010110' in analytics['activities']:
            lines.append({
                'account_id': accounts['budget_account_5101020045'].id,
                'activity_analytic_id': analytics['activities']['activity_09007010110'].id,
                'department_analytic_id': refs['dept_02'].id,
                'fund_analytic_id': analytics['funds']['fund_0100'].id,
                'source_analytic_id': refs['source_2'].id,
                'balance': 800000.0,
                'name': 'Demo: Utilities and operating expenses',
            })
        
        return lines

    def _create_equipment_lines(self, refs):
        """Create equipment purchase budget lines"""
        lines = []
        analytics = refs['analytics']
        accounts = refs['budget_accounts']
        
        if 'budget_account_5104010203' in accounts and 'activity_09007010111' in analytics['activities']:
            lines.append({
                'account_id': accounts['budget_account_5104010203'].id,
                'activity_analytic_id': analytics['activities']['activity_09007010111'].id,
                'department_analytic_id': refs['dept_02'].id,
                'fund_analytic_id': analytics['funds']['fund_0200'].id,
                'source_analytic_id': refs['source_2'].id,
                'balance': 2000000.0,
                'name': 'Demo: IT equipment and software',
            })
        
        return lines

    def _create_travel_lines(self, refs):
        """Create travel and training budget lines"""
        lines = []
        analytics = refs['analytics']
        accounts = refs['budget_accounts']
        
        if 'budget_account_5107010500' in accounts and 'activity_090100201' in analytics['activities']:
            lines.append({
                'account_id': accounts['budget_account_5107010500'].id,
                'activity_analytic_id': analytics['activities']['activity_090100201'].id,
                'department_analytic_id': refs['dept_02'].id,
                'fund_analytic_id': analytics['funds']['fund_0600'].id,
                'source_analytic_id': refs['source_2'].id,
                'balance': 500000.0,
                'name': 'Demo: Academic travel and training',
            })
        
        return lines

    def _create_special_activity_lines(self, refs):
        """Create special activity budget lines"""
        lines = []
        analytics = refs['analytics']
        accounts = refs['budget_accounts']
        
        if 'budget_account_5108000020' in accounts and 'activity_09007010110' in analytics['activities']:
            lines.append({
                'account_id': accounts['budget_account_5108000020'].id,
                'activity_analytic_id': analytics['activities']['activity_09007010110'].id,
                'department_analytic_id': refs['dept_02'].id,
                'fund_analytic_id': analytics['funds']['fund_0100'].id,
                'source_analytic_id': refs['source_2'].id,
                'balance': 1000000.0,
                'name': 'Demo: Special faculty development activities',
            })
        
        return lines


    def _create_dept03_budget_move(self, refs):
        """Create Department 03 revenue budget appropriation move"""
        try:
            if not refs['dept_01'] or not refs['revenue_journal']:
                _logger.warning("Missing dept_01 or revenue_journal for dept03 move")
                return None
                
            move_vals = {
                'name': 'DEMO_DEPT03_REVENUE_2568',
                'move_type': 'appropriation',
                'is_initial_appropriation': True,
                'date': date(2024, 10, 1),
                'date_range_fy_id': refs['fiscal_year'].id,
                'department_analytic_id': refs['dept_01'].id,
                'source_analytic_id': refs['source_2'].id,
                'journal_id': refs['revenue_journal'].id,
                'ref': 'Demo: Revenue Budget Appropriation FY2568',
                'state': 'draft',
            }
            
            # Create simple revenue lines
            lines = []
            analytics = refs['analytics']
            
            if analytics['activities'] and analytics['funds']:
                # Pick first available activity and fund
                activity = list(analytics['activities'].values())[0]
                fund = list(analytics['funds'].values())[0]
                
                lines.append({
                    'account_id': list(refs['budget_accounts'].values())[0].id,  # Use first available account
                    'activity_analytic_id': activity.id,
                    'department_analytic_id': refs['dept_01'].id,
                    'fund_analytic_id': fund.id,
                    'source_analytic_id': refs['source_2'].id,
                    'balance': 3000000.0,
                    'name': 'Demo: Revenue budget allocation',
                    })
            
            move_vals['line_ids'] = [(0, 0, line) for line in lines]
            
            # Create the move
            move = self.env['budget.move'].create(move_vals)
            _logger.info(f"Created demo revenue budget move: {move.name}")
            
            return move
            
        except Exception as e:
            _logger.error(f"Failed to create dept03 budget move: {str(e)}")
            return None

    def _create_multi_activity_budget_move(self, refs):
        """Create a budget move demonstrating multiple activities"""
        try:
            move_vals = {
                'name': 'DEMO_MULTI_ACTIVITY_2568',
                'move_type': 'appropriation',
                'is_initial_appropriation': True,
                'date': date(2024, 10, 15),
                'date_range_fy_id': refs['fiscal_year'].id,
                'department_analytic_id': refs['dept_02'].id,
                'source_analytic_id': refs['source_2'].id,
                'journal_id': refs['expense_journal'].id,
                'ref': 'Demo: Multi-Activity Budget Distribution',
                'state': 'draft',
            }
            
            lines = []
            analytics = refs['analytics']
            accounts = refs['budget_accounts']
            
            # Create lines across different activities if available
            if len(analytics['activities']) >= 2 and len(analytics['funds']) >= 2:
                activities = list(analytics['activities'].values())
                funds = list(analytics['funds'].values())
                account_keys = list(accounts.keys())
                
                if account_keys:
                    # Create lines for different activity-fund combinations
                    for i, (activity, fund) in enumerate(zip(activities[:2], funds[:2])):
                        if i < len(account_keys):
                            account_key = account_keys[i]
                            lines.append({
                                'account_id': accounts[account_key].id,
                                'activity_analytic_id': activity.id,
                                'department_analytic_id': refs['dept_02'].id,
                                'fund_analytic_id': fund.id,
                                'source_analytic_id': refs['source_2'].id,
                                'balance': 750000.0 * (i + 1),
                                'name': f'Demo: Multi-activity allocation {i+1}',
                                            })
            
            if lines:
                move_vals['line_ids'] = [(0, 0, line) for line in lines]
                
                # Create the move
                move = self.env['budget.move'].create(move_vals)
                _logger.info(f"Created demo multi-activity budget move: {move.name}")
                
                return move
            else:
                _logger.warning("No lines created for multi-activity move")
                return None
            
        except Exception as e:
            _logger.error(f"Failed to create multi-activity budget move: {str(e)}")
            return None

    def _create_csv_based_budget_moves(self, refs):
        """Create comprehensive budget moves matching the CSV data"""
        moves = []
        
        try:
            # Create the comprehensive Department 02 move (CSV equivalent)
            csv_dept02_move = self._create_comprehensive_dept02_move(refs)
            if csv_dept02_move:
                moves.append(csv_dept02_move)
            
            # Create the revenue move (CSV equivalent) 
            csv_dept03_move = self._create_comprehensive_dept03_move(refs)
            if csv_dept03_move:
                moves.append(csv_dept03_move)
                
            return moves
            
        except Exception as e:
            _logger.error(f"Failed to create CSV-based budget moves: {str(e)}")
            return []

    def _create_comprehensive_dept02_move(self, refs):
        """Create comprehensive Department 02 move matching CSV data"""
        try:
            move_vals = {
                'name': 'DEMO_CSV_DEPT02_COMPREHENSIVE_2568',
                'move_type': 'appropriation',
                'is_initial_appropriation': True,
                'date': date(2024, 10, 1),
                'date_range_fy_id': refs['fiscal_year'].id,
                'department_analytic_id': refs['dept_02'].id,
                'source_analytic_id': refs['source_2'].id,
                'journal_id': refs['expense_journal'].id,
                'ref': 'Demo: เงินจัดสรรอนุมัติสภาสถาบัน (CSV Based)',
                'state': 'draft',
            }
            
            # Get required analytic accounts from CSV data
            activity_110 = self.env.ref('account_analytic_kmitl.activity_09007010110', raise_if_not_found=False)
            activity_111 = self.env.ref('account_analytic_kmitl.activity_09007010111', raise_if_not_found=False)
            activity_115 = self.env.ref('account_analytic_kmitl.activity_09007010115', raise_if_not_found=False)
            activity_116 = self.env.ref('account_analytic_kmitl.activity_09007010116', raise_if_not_found=False)
            activity_118 = self.env.ref('account_analytic_kmitl.activity_09007010118', raise_if_not_found=False)
            activity_119 = self.env.ref('account_analytic_kmitl.activity_09007010119', raise_if_not_found=False)
            activity_223211 = self.env.ref('account_analytic_kmitl.activity_09007010223211', raise_if_not_found=False)
            activity_223212 = self.env.ref('account_analytic_kmitl.activity_09007010223212', raise_if_not_found=False)
            activity_201 = self.env.ref('account_analytic_kmitl.activity_090100201', raise_if_not_found=False)
            activity_060040401 = self.env.ref('account_analytic_kmitl.activity_060040401', raise_if_not_found=False)
            
            # Get fund references
            fund_0100 = self.env.ref('account_analytic_kmitl.fund_0100', raise_if_not_found=False)
            fund_0200 = self.env.ref('account_analytic_kmitl.fund_0200', raise_if_not_found=False)
            fund_0300 = self.env.ref('account_analytic_kmitl.fund_0300', raise_if_not_found=False)
            fund_0400 = self.env.ref('account_analytic_kmitl.fund_0400', raise_if_not_found=False)
            fund_0500 = self.env.ref('account_analytic_kmitl.fund_0500', raise_if_not_found=False)
            fund_0600 = self.env.ref('account_analytic_kmitl.fund_0600', raise_if_not_found=False)
            fund_0703 = self.env.ref('account_analytic_kmitl.fund_0703', raise_if_not_found=False)
            fund_0705 = self.env.ref('account_analytic_kmitl.fund_0705', raise_if_not_found=False)
            
            # Create comprehensive budget lines matching CSV data
            lines = self._get_comprehensive_budget_lines(refs, {
                'activity_110': activity_110,
                'activity_111': activity_111,
                'activity_115': activity_115,
                'activity_116': activity_116,
                'activity_118': activity_118,
                'activity_119': activity_119,
                'activity_223211': activity_223211,
                'activity_223212': activity_223212,
                'activity_201': activity_201,
                'activity_060040401': activity_060040401,
                'fund_0100': fund_0100,
                'fund_0200': fund_0200,
                'fund_0300': fund_0300,
                'fund_0400': fund_0400,
                'fund_0500': fund_0500,
                'fund_0600': fund_0600,
                'fund_0703': fund_0703,
                'fund_0705': fund_0705,
            })
            
            if not lines:
                _logger.warning("No comprehensive budget lines created - missing reference data")
                return None
            
            move_vals['line_ids'] = [(0, 0, line) for line in lines]
            
            # Create the move
            move = self.env['budget.move'].create(move_vals)
            _logger.info(f"Created comprehensive CSV-based budget move: {move.name}")
            
            return move
            
        except Exception as e:
            _logger.error(f"Failed to create comprehensive dept02 move: {str(e)}")
            return None

    def _get_comprehensive_budget_lines(self, refs, analytics):
        """Get comprehensive budget lines matching CSV data structure"""
        lines = []
        
        # Define the budget line data matching the CSV
        budget_line_data = [
            # Activity 09007010110 - Fund 0100
            ('budget.budget_account_5101010038', 'activity_110', 'fund_0100', 10450500.0, ''),
            ('budget.budget_account_5101010004', 'activity_110', 'fund_0100', 2702400.0, ''),
            ('budget.budget_account_5101020045', 'activity_110', 'fund_0100', 300700.0, ''),
            ('budget.budget_account_5101020051', 'activity_110', 'fund_0100', 211100.0, ''),
            ('budget.budget_account_5101030245', 'activity_110', 'fund_0100', 1291700.0, ''),
            ('budget.budget_account_5101010010', 'activity_110', 'fund_0100', 50000.0, ''),
            ('budget.budget_account_5104030201', 'activity_110', 'fund_0100', 50000.0, ''),
            ('budget.budget_account_5101020014', 'activity_110', 'fund_0100', 50000.0, ''),
            ('budget.budget_account_5101020030', 'activity_110', 'fund_0100', 50000.0, ''),
            ('budget.budget_account_5101020037', 'activity_110', 'fund_0100', 50000.0, ''),
            ('budget.budget_account_5104010202', 'activity_110', 'fund_0100', 343000.0, ''),
            ('budget.budget_account_5104010201', 'activity_110', 'fund_0100', 50000.0, ''),
            ('budget.budget_account_5104010203', 'activity_110', 'fund_0100', 13000000.0, ''),
            ('budget.budget_account_5103010000', 'activity_110', 'fund_0100', 200000.0, ''),
            ('budget.budget_account_5103020000', 'activity_110', 'fund_0100', 200000.0, ''),
            ('budget.budget_account_5104010208', 'activity_110', 'fund_0100', 200000.0, ''),
            ('budget.budget_account_5104030101', 'activity_110', 'fund_0100', 207000.0, ''),
            ('budget.budget_account_5104010101', 'activity_110', 'fund_0100', 144700.0, ''),
            ('budget.budget_account_5104010104', 'activity_110', 'fund_0100', 50000.0, ''),
            ('budget.budget_account_5104010105', 'activity_110', 'fund_0100', 50000.0, ''),
            ('budget.budget_account_5104010102', 'activity_110', 'fund_0100', 50000.0, ''),
            ('budget.budget_account_5104010109', 'activity_110', 'fund_0100', 50000.0, ''),
            ('budget.budget_account_5104010111', 'activity_110', 'fund_0100', 50000.0, ''),
            ('budget.budget_account_5104010112', 'activity_110', 'fund_0100', 50000.0, ''),
            ('budget.budget_account_5104020003', 'activity_110', 'fund_0100', 1000000.0, ''),
            ('budget.budget_account_5104020001', 'activity_110', 'fund_0100', 2500000.0, ''),
            ('budget.budget_account_5104020005', 'activity_110', 'fund_0100', 450000.0, ''),
            ('budget.budget_account_5104020008', 'activity_110', 'fund_0100', 50000.0, ''),
            ('budget.budget_account_5107010044', 'activity_110', 'fund_0100', 10000.0, ''),
            ('budget.budget_account_5107010088', 'activity_110', 'fund_0100', 50000.0, ''),
            ('budget.budget_account_5108000024', 'activity_110', 'fund_0100', 150000.0, ''),
            ('budget.budget_account_5108000020', 'activity_110', 'fund_0100', 4403300.0, 'ค่าใช้จ่ายในการดําเนินกิจกรมพิเศษ 2,000,000 บาท\\r\\nรายจ่ายอื่นค่าใช้จ่ายในการดําเนินกิจกรรมพิเศษรายจ่ายอื่น(ภาควิชา) 3,365,400 บาท \\r\\n ค่าใช้จ่ายในการดําเนินกิจกรรมพิเศษรายจ่ายอื่น(ผู้บริหาร) อาทิเช่นกิจกรรมขอบคุณบุคลากร/มุทิตาจิต/สถาปนาคณะเป็นต้น 837,900 บาท'),
            ('budget.budget_account_5108000003', 'activity_110', 'fund_0100', 50000.0, ''),
            
            # Activity 09007010110 - Fund 0600
            ('budget.budget_account_5104010204', 'activity_110', 'fund_0600', 150000.0, ''),
            ('budget.budget_account_5104010206', 'activity_110', 'fund_0600', 150000.0, ''),
            ('budget.budget_account_5104010106', 'activity_110', 'fund_0600', 100000.0, ''),
            ('budget.budget_account_5104030209', 'activity_110', 'fund_0600', 1050000.0, ''),
            ('budget.budget_account_5411000004', 'activity_110', 'fund_0600', 1050000.0, ''),
            ('budget.budget_account_702', 'activity_110', 'fund_0600', 12707600.0, ''),
            
            # Activity 09007010111 - Fund 0100
            ('budget.budget_account_5101010010', 'activity_111', 'fund_0100', 50000.0, ''),
            ('budget.budget_account_5101020019', 'activity_111', 'fund_0100', 130000.0, ''),
            ('budget.budget_account_5104010101', 'activity_111', 'fund_0100', 10000.0, ''),
            ('budget.budget_account_5104010109', 'activity_111', 'fund_0100', 10000.0, ''),
            ('budget.budget_account_5108000008', 'activity_111', 'fund_0100', 200000.0, ''),
            ('budget.budget_account_5108000009', 'activity_111', 'fund_0100', 20000.0, ''),
            
            # Activity 09007010115 - Fund 0500, 0705
            ('budget.budget_account_5107010022', 'activity_115', 'fund_0500', 30000.0, ''),
            ('budget.budget_account_5107010501', 'activity_115', 'fund_0705', 2920000.0, ''),
            
            # Activity 09007010116 - Fund 0703, 0705
            ('budget.budget_account_5102010000', 'activity_116', 'fund_0703', 315000.0, ''),
            ('budget.budget_account_5102020000', 'activity_116', 'fund_0703', 100000.0, ''),
            ('budget.budget_account_5107010500', 'activity_116', 'fund_0705', 223000.0, 'Academic'),
            ('budget.budget_account_5107010500', 'activity_116', 'fund_0705', 881600.0, 'Education'),
            
            # Activity 09007010118 - Fund 0200, 0705
            ('budget.budget_account_5104030201', 'activity_118', 'fund_0200', 30000.0, ''),
            ('budget.budget_account_5107010500', 'activity_118', 'fund_0705', 500000.0, 'Education'),
            
            # Activity 09007010119 - Fund 0200
            ('budget.budget_account_5104010101', 'activity_119', 'fund_0200', 200000.0, ''),
            
            # Activity 09007010223211 - Fund 0200, 0600
            ('budget.budget_account_5101010010', 'activity_223211', 'fund_0200', 42500.0, ''),
            ('budget.budget_account_5101020012', 'activity_223211', 'fund_0200', 3494900.0, ''),
            ('budget.budget_account_5101020018', 'activity_223211', 'fund_0200', 202500.0, ''),
            ('budget.budget_account_5101020011', 'activity_223211', 'fund_0200', 2482000.0, ''),
            ('budget.budget_account_5103010000', 'activity_223211', 'fund_0200', 69500.0, 'เกี่ยวกับนักศึกษา'),
            ('budget.budget_account_5104010203', 'activity_223211', 'fund_0200', 262500.0, ''),
            ('budget.budget_account_5104010103', 'activity_223211', 'fund_0200', 1241400.0, ''),
            ('budget.budget_account_5412000003', 'activity_223211', 'fund_0600', 82100.0, ''),
            
            # Activity 09007010223212 - Fund 0200
            ('budget.budget_account_5101020013', 'activity_223212', 'fund_0200', 362600.0, ''),
            ('budget.budget_account_5101020018', 'activity_223212', 'fund_0200', 402800.0, ''),
            ('budget.budget_account_5101020011', 'activity_223212', 'fund_0200', 167300.0, ''),
            ('budget.budget_account_5101010010', 'activity_223212', 'fund_0200', 30300.0, ''),
            ('budget.budget_account_5103010000', 'activity_223212', 'fund_0200', 54000.0, 'เกี่ยวกับนักศึกษา'),
            ('budget.budget_account_5104010203', 'activity_223212', 'fund_0200', 122500.0, ''),
            ('budget.budget_account_5104010103', 'activity_223212', 'fund_0200', 135600.0, ''),
            
            # Activity 090100201 - Fund 0400, 0705
            ('budget.budget_account_5101020104', 'activity_201', 'fund_0400', 60000.0, ''),
            ('budget.budget_account_5104010203', 'activity_201', 'fund_0400', 40000.0, ''),
            ('budget.budget_account_5107010500', 'activity_201', 'fund_0705', 3698000.0, 'Educational'),
            ('budget.budget_account_5107010500', 'activity_201', 'fund_0705', 192400.0, 'Educational (ภาค)'),
            
            # Activity 060040401 - Fund 0300
            ('budget.budget_account_5107010202', 'activity_060040401', 'fund_0300', 3700000.0, ''),
        ]
        
        # Create budget lines from the data
        for account_ref, activity_key, fund_key, amount, note in budget_line_data:
            account = self.env.ref(account_ref, raise_if_not_found=False)
            activity = analytics.get(activity_key)
            fund = analytics.get(fund_key)
            
            if account and activity and fund:
                lines.append({
                    'account_id': account.id,
                    'activity_analytic_id': activity.id,
                    'department_analytic_id': refs['dept_02'].id,
                    'fund_analytic_id': fund.id,
                    'source_analytic_id': refs['source_2'].id,
                    'balance': amount,
                    'name': f"CSV Demo: {account.name}" + (f" - {note}" if note else ""),
                    })
            else:
                missing = []
                if not account: missing.append(f"account({account_ref})")
                if not activity: missing.append(f"activity({activity_key})")
                if not fund: missing.append(f"fund({fund_key})")
                _logger.debug(f"Skipping line due to missing references: {missing}")
        
        return lines

    def _create_comprehensive_dept03_move(self, refs):
        """Create comprehensive Department 03 revenue move matching CSV"""
        try:
            if not refs.get('dept_01') or not refs.get('revenue_journal'):
                _logger.warning("Missing dept_01 or revenue_journal for comprehensive dept03 move")
                return None
                
            move_vals = {
                'name': 'DEMO_CSV_DEPT03_REVENUE_2568',
                'move_type': 'appropriation',
                'is_initial_appropriation': True,
                'date': date(2024, 10, 1),
                'date_range_fy_id': refs['fiscal_year'].id,
                'department_analytic_id': refs['dept_01'].id,
                'source_analytic_id': refs['source_2'].id,
                'journal_id': refs['revenue_journal'].id,
                'ref': 'Demo: ประมาณการรายรับเงินรายได้ (CSV Based)',
                'state': 'draft',
            }
            
            # Create lines similar to the CSV data (simplified for revenue)
            lines = []
            
            # Get a revenue budget account for the demo
            revenue_account = self.env.ref('budget.budget_account_5101010038', raise_if_not_found=False)
            activity = self.env.ref('account_analytic_kmitl.activity_09007010110', raise_if_not_found=False)
            fund = self.env.ref('account_analytic_kmitl.fund_0100', raise_if_not_found=False)
            
            if revenue_account and activity and fund:
                lines.append({
                    'account_id': revenue_account.id,
                    'activity_analytic_id': activity.id,
                    'department_analytic_id': refs['dept_01'].id,
                    'fund_analytic_id': fund.id,
                    'source_analytic_id': refs['source_2'].id,
                    'balance': 5000000.0,  # 5M THB revenue allocation
                    'name': 'CSV Demo: Revenue budget allocation',
                    })
            
            if lines:
                move_vals['line_ids'] = [(0, 0, line) for line in lines]
                
                # Create the move
                move = self.env['budget.move'].create(move_vals)
                _logger.info(f"Created comprehensive CSV-based revenue move: {move.name}")
                
                return move
            else:
                _logger.warning("No lines created for comprehensive dept03 revenue move")
                return None
            
        except Exception as e:
            _logger.error(f"Failed to create comprehensive dept03 move: {str(e)}")
            return None

    @api.model
    def remove_demo_data(self):
        """Remove all demo budget moves (for cleanup)"""
        try:
            demo_moves = self.env['budget.move'].search([
                ('name', 'like', 'DEMO_%'),
                ('move_type', '=', 'appropriation'),
            ('is_initial_appropriation', '=', True)
            ])
            
            if demo_moves:
                # Cancel moves first if posted
                posted_moves = demo_moves.filtered(lambda m: m.state == 'posted')
                if posted_moves:
                    posted_moves.button_cancel()
                
                # Delete moves
                demo_moves.unlink()
                _logger.info(f"Removed {len(demo_moves)} demo budget moves")
                
            return True
            
        except Exception as e:
            _logger.error(f"Failed to remove demo data: {str(e)}")
            return False

    @api.model
    def get_demo_data_info(self):
        """Get information about existing demo data"""
        demo_moves = self.env['budget.move'].search([
            ('name', 'like', 'DEMO_%'),
            ('move_type', '=', 'appropriation'),
            ('is_initial_appropriation', '=', True)
        ])
        
        if not demo_moves:
            return {
                'exists': False,
                'count': 0,
                'moves': [],
                'total_amount': 0.0,
            }
        
        move_info = []
        total_amount = 0.0
        
        for move in demo_moves:
            # Calculate total amount from non-virtual lines
            real_lines = move.line_ids.filtered(lambda l: not l.is_virtual_line)
            move_total = sum(real_lines.mapped('balance'))
            total_amount += move_total
            
            move_info.append({
                'name': move.name,
                'date': move.date,
                'state': move.state,
                'department': move.department_analytic_id.name if move.department_analytic_id else '',
                'total_amount': move_total,
                'line_count': len(real_lines),
            })
        
        return {
            'exists': True,
            'count': len(demo_moves),
            'moves': move_info,
            'total_amount': total_amount,
            'currencies': demo_moves.mapped('company_id.currency_id.name'),
        }