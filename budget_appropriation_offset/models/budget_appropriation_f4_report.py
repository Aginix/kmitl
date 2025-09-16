import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class BudgetAppropriationF4ReportOffset(models.TransientModel):
    _inherit = "budget.appropriation.f4.report"

    @api.model
    def get_f4_data(self, appropriation_id, options=None):
        """Enhanced F4 data with offset information for revenue appropriations"""
        # Get base F4 data from parent
        result = super().get_f4_data(appropriation_id, options)
        
        if result.get("error"):
            return result
            
        appropriation = self.env["budget.appropriation"].browse(appropriation_id)
        
        if not appropriation or appropriation.budget_type != 'revenue':
            return result
        
        # Enhance appropriation data with offset information
        if "appropriation" in result:
            result["appropriation"].update({
                "offset_total": appropriation.offset_total,
                "total_revenue_net": appropriation.total_revenue_net,
                "has_offsets": bool(appropriation.offset_ids),
            })
        
        # Add offset details to summary
        if "summary" in result:
            result["summary"].update({
                "offset_total": appropriation.offset_total,
                "total_revenue_net": appropriation.total_revenue_net,
                "offsets_count": len(appropriation.offset_ids),
            })
        
        # Enhance hierarchy with offset data
        if "hierarchy" in result:
            result["hierarchy"] = self._enhance_hierarchy_with_offsets(result["hierarchy"], appropriation)
        
        return result
    
    def _enhance_hierarchy_with_offsets(self, hierarchy, appropriation):
        """Enhance hierarchy nodes with offset information"""
        enhanced_hierarchy = []
        
        for node in hierarchy:
            enhanced_node = dict(node)
            enhanced_node = self._add_offset_data_to_node(enhanced_node, appropriation)
            enhanced_hierarchy.append(enhanced_node)
        
        return enhanced_hierarchy
    
    def _add_offset_data_to_node(self, node, appropriation):
        """Recursively add offset data to hierarchy nodes"""
        # Add offset data to account nodes that have line details
        if node.get('type') == 'account' and node.get('line_details'):
            node['offsets'] = []
            total_node_offsets = 0
            
            # Find offsets for this account's lines
            for line_detail in node.get('line_details', []):
                line_id = line_detail.get('id')
                if line_id:
                    line = appropriation.line_ids.filtered(lambda l: l.id == line_id)
                    if line and line.offset_ids:
                        for offset in line.offset_ids:
                            offset_data = {
                                'id': offset.id,
                                'name': offset.name or f"หักโอน {offset.amount:,.0f} บาท",
                                'amount': offset.amount,
                                'note': offset.note,
                                'state': offset.state,
                                'state_label': dict(offset._fields['state'].selection).get(offset.state, offset.state),
                                'from_department': {
                                    'id': offset.from_department_analytic_id.id,
                                    'name': offset.from_department_analytic_id.name,
                                    'code': offset.from_department_analytic_id.code,
                                } if offset.from_department_analytic_id else None,
                                'to_department': {
                                    'id': offset.to_department_analytic_id.id,
                                    'name': offset.to_department_analytic_id.name,
                                    'code': offset.to_department_analytic_id.code,
                                } if offset.to_department_analytic_id else None,
                            }
                            node['offsets'].append(offset_data)
                            total_node_offsets += offset.amount
            
            # Update node amounts to show net after offsets
            if total_node_offsets > 0:
                node['offset_total'] = total_node_offsets
                node['amount_before_offset'] = node.get('amount', 0)
                node['net_amount'] = node.get('total_amount', 0) - total_node_offsets
                node['has_offsets'] = True
            else:
                node['offset_total'] = 0
                node['net_amount'] = node.get('total_amount', 0)
                node['has_offsets'] = False
        
        # Recursively process children
        if 'children' in node and node['children']:
            enhanced_children = []
            for child in node['children']:
                enhanced_child = self._add_offset_data_to_node(child, appropriation)
                enhanced_children.append(enhanced_child)
            node['children'] = enhanced_children
        
        return node