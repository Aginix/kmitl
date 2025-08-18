"""
Budget Tree Builder - Reusable component for building hierarchical budget data

This module provides a flexible tree building system that can work with different
budget models (appropriation, move, commitment) and various dimension configurations.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Callable

_logger = logging.getLogger(__name__)


class TreeConfig:
    """Configuration class for tree building"""
    
    def __init__(self, 
                 dimensions: List[str] = None,
                 include_empty: bool = False,
                 calculate_rollups: bool = True,
                 max_depth: Optional[int] = None,
                 filters: Dict[str, Any] = None,
                 amount_field: str = 'balance',
                 custom_name_cleaner: Optional[Callable] = None):
        """
        Initialize tree configuration
        
        Args:
            dimensions: List of dimensions to build (e.g., ['activity', 'fund', 'account'])
            include_empty: Whether to include lines with zero amounts
            calculate_rollups: Whether to calculate total amounts recursively
            max_depth: Maximum tree depth (None for unlimited)
            filters: Additional filters to apply to lines
            amount_field: Field name to use for amounts (balance, amount, debit-credit, etc.)
            custom_name_cleaner: Custom function to clean record names
        """
        self.dimensions = dimensions or ['activity', 'fund', 'account']
        self.include_empty = include_empty
        self.calculate_rollups = calculate_rollups
        self.max_depth = max_depth
        self.filters = filters or {}
        self.amount_field = amount_field
        self.custom_name_cleaner = custom_name_cleaner
    
    @classmethod
    def for_f5_report(cls):
        """Predefined config for F5 reports"""
        return cls(
            dimensions=['activity', 'fund', 'account'],
            include_empty=False,
            calculate_rollups=True,
            amount_field='balance'
        )
    
    @classmethod
    def for_budget_moves(cls):
        """Predefined config for budget moves"""
        return cls(
            dimensions=['activity', 'fund', 'account'],
            include_empty=False,
            calculate_rollups=True,
            amount_field='amount'
        )
    
    @classmethod
    def for_commitments(cls):
        """Predefined config for budget commitments"""
        return cls(
            dimensions=['activity', 'fund', 'account'],
            include_empty=False,
            calculate_rollups=True,
            amount_field='amount'
        )


class TreeNode:
    """Enhanced tree node with additional functionality"""
    
    def __init__(self, node_type: str = 'root', node_id: int = None, 
                 code: str = '', name: str = 'Root'):
        # Identity
        self.node_type = node_type
        self.node_id = node_id
        self.code = code
        self.name = name
        self.complete_name = name
        
        # Tree structure
        self.parent = None
        self.children = []
        self.level = 0
        
        # Financial data
        self.amount = 0.0
        self.total_amount = 0.0
        
        # Metadata
        self.metadata = {
            'line_ids': [],
            'line_count': 0,
            'has_data': False,
            'expanded': True,
            'res_model': None,
            'res_id': None,
            'created_at': None,
            'custom_data': {}
        }
    
    def add_child(self, child: 'TreeNode') -> 'TreeNode':
        """Add child node and set relationships"""
        child.parent = self
        child.level = self.level + 1
        self.children.append(child)
        return child
    
    def find_child(self, node_type: str, node_id: int) -> Optional['TreeNode']:
        """Find direct child by type and ID"""
        for child in self.children:
            if child.node_type == node_type and child.node_id == node_id:
                return child
        return None
    
    def find_or_create_child(self, node_type: str, node_id: int, 
                           code: str = '', name: str = '') -> 'TreeNode':
        """Find existing child or create new one"""
        existing = self.find_child(node_type, node_id)
        if existing:
            return existing
        
        new_child = TreeNode(node_type, node_id, code, name)
        return self.add_child(new_child)
    
    def to_dict(self, include_children: bool = True) -> Dict[str, Any]:
        """Convert node to dictionary representation"""
        data = {
            'type': self.node_type,
            'key': f"{self.node_type}_{self.node_id}",
            'id': self.node_id,
            'code': self.code,
            'name': self.name,
            'complete_name': self.complete_name,
            'amount': self.amount,
            'total_amount': self.total_amount,
            'level': self.level,
            'has_data': self.metadata.get('has_data', False),
            'expanded': self.metadata.get('expanded', True),
            'line_details': []
        }
        
        # Add line details if available
        if 'line_details' in self.metadata:
            data['line_details'] = self.metadata['line_details']
        
        # Add children if requested
        if include_children and self.children:
            data['children'] = [
                child.to_dict(include_children=True) 
                for child in self.children
            ]
        
        return data
    
    def get_path(self) -> List['TreeNode']:
        """Get path from root to this node"""
        path = []
        current = self
        while current:
            path.insert(0, current)
            current = current.parent
        return path
    
    def calculate_rollups(self) -> float:
        """Calculate total amounts recursively"""
        if not self.children:
            self.total_amount = self.amount
            return self.total_amount
        
        total = self.amount
        for child in self.children:
            total += child.calculate_rollups()
        
        self.total_amount = total
        return total


class BudgetTreeBuilder:
    """Enhanced tree builder with flexible configuration"""
    
    def __init__(self, config: TreeConfig = None):
        """
        Initialize tree builder with configuration
        
        Args:
            config: TreeConfig instance with building parameters
        """
        self.config = config or TreeConfig()
        self.root = TreeNode()
        self.node_cache = {}
        self._dimension_field_map = {
            'activity': 'activity_analytic_id',
            'fund': 'fund_analytic_id', 
            'account': 'account_id',
            'department': 'department_analytic_id',
            'source': 'source_analytic_id'
        }
    
    def build_tree(self, lines) -> TreeNode:
        """
        Build tree from budget lines
        
        Args:
            lines: Odoo recordset of budget lines
            
        Returns:
            TreeNode: Root node of the built tree
        """
        _logger.info(f"Building tree from {len(lines)} lines with config: {self.config.dimensions}")
        
        # Filter lines based on configuration
        filtered_lines = self._filter_lines(lines)
        _logger.info(f"Filtered to {len(filtered_lines)} lines")
        
        # Process each line
        for line in filtered_lines:
            self._process_line(line)
        
        # Calculate totals if configured
        if self.config.calculate_rollups:
            self.root.calculate_rollups()
        
        _logger.info(f"Tree built successfully with {len(self.root.children)} top-level nodes")
        return self.root
    
    def get_hierarchy(self) -> List[Dict[str, Any]]:
        """Get hierarchy as list of dictionaries (compatible with existing F5)"""
        return [child.to_dict() for child in self.root.children]
    
    def _process_line(self, line):
        """Process a single budget line and add to tree"""
        current = self.root
        depth = 0
        
        # Build path through configured dimensions
        for dimension in self.config.dimensions:
            # Check max depth
            if self.config.max_depth and depth >= self.config.max_depth:
                break
            
            # Get record for this dimension
            field_name = self._dimension_field_map.get(dimension)
            if not field_name:
                _logger.warning(f"Unknown dimension: {dimension}")
                continue
            
            record = getattr(line, field_name, None)
            if not record:
                continue
            
            # Build hierarchy path for this dimension
            hierarchy_path = self._get_record_hierarchy_path(record)
            current = self._build_dimension_path(current, dimension, hierarchy_path, depth)
            depth += len(hierarchy_path)
        
        # Add line data to final node
        self._add_line_data(current, line)
    
    def _filter_lines(self, lines):
        """Filter lines based on configuration"""
        filtered = lines
        
        # Filter by amount if not including empty
        if not self.config.include_empty:
            filtered = filtered.filtered(
                lambda l: self._get_line_amount(l) != 0
            )
        
        # Apply additional filters
        for field, value in self.config.filters.items():
            if isinstance(value, tuple) and len(value) == 2:
                operator, val = value
                if operator == '!=':
                    filtered = filtered.filtered(lambda l: getattr(l, field, None) != val)
                elif operator == '=':
                    filtered = filtered.filtered(lambda l: getattr(l, field, None) == val)
                elif operator == '>':
                    filtered = filtered.filtered(lambda l: getattr(l, field, 0) > val)
                elif operator == '<':
                    filtered = filtered.filtered(lambda l: getattr(l, field, 0) < val)
            else:
                filtered = filtered.filtered(lambda l: getattr(l, field, None) == value)
        
        return filtered
    
    def _get_record_hierarchy_path(self, record) -> List:
        """Get full hierarchy path for a record"""
        if not record:
            return []
        
        path = []
        current = record
        while current:
            path.insert(0, current)
            current = getattr(current, 'parent_id', None)
        
        return path
    
    def _build_dimension_path(self, parent: TreeNode, dimension: str, 
                            records: List, base_depth: int) -> TreeNode:
        """Build path for a dimension through its hierarchy"""
        current = parent
        
        for i, record in enumerate(records):
            # Create cache key including parent context
            cache_key = f"{dimension}_{record.id}"
            if current.node_id:
                cache_key += f"_ctx_{current.node_id}"
            
            # Check cache
            if cache_key in self.node_cache:
                current = self.node_cache[cache_key]
            else:
                # Create new node
                node = self._create_node(dimension, record, current)
                current.add_child(node)
                self.node_cache[cache_key] = node
                current = node
        
        return current
    
    def _create_node(self, node_type: str, record, parent: TreeNode) -> TreeNode:
        """Create a new tree node from a record"""
        node = TreeNode(
            node_type=node_type,
            node_id=record.id,
            code=getattr(record, 'code', ''),
            name=record.name
        )
        
        # Set complete name
        node.complete_name = self._clean_record_name(record)
        
        # Set metadata
        node.metadata.update({
            'res_model': record._name,
            'res_id': record.id,
            'line_details': []
        })
        
        return node
    
    def _add_line_data(self, node: TreeNode, line):
        """Add line data to a node"""
        amount = self._get_line_amount(line)
        node.amount += amount
        node.metadata['has_data'] = True
        node.metadata['line_count'] += 1
        node.metadata['line_ids'].append(line.id)
        
        # Store line details
        if 'line_details' not in node.metadata:
            node.metadata['line_details'] = []
        
        node.metadata['line_details'].append({
            'id': line.id,
            'note': getattr(line, 'note', ''),
            'balance': amount,
            'amount': amount
        })
    
    def _get_line_amount(self, line) -> float:
        """Get amount from line based on configuration"""
        field = self.config.amount_field
        
        if field == 'balance':
            return getattr(line, 'balance', 0.0)
        elif field == 'amount':
            return getattr(line, 'amount', 0.0)
        elif field == 'debit-credit':
            debit = getattr(line, 'debit', 0.0)
            credit = getattr(line, 'credit', 0.0)
            return debit - credit
        else:
            return getattr(line, field, 0.0)
    
    def _clean_record_name(self, record) -> str:
        """Clean record name using configured cleaner or default"""
        if self.config.custom_name_cleaner:
            return self.config.custom_name_cleaner(record)
        
        return self._default_name_cleaner(record)
    
    def _default_name_cleaner(self, record) -> str:
        """Default name cleaner - removes [code] patterns"""
        if not record:
            return ""
        
        if hasattr(record, 'complete_name') and record.complete_name:
            return re.sub(r'\[.*?\]\s*', '', record.complete_name)
        return record.name


class BudgetTreeExporter:
    """Export tree to various formats"""
    
    @staticmethod
    def to_odoo_hierarchy(tree: TreeNode) -> List[Dict[str, Any]]:
        """Export to Odoo-compatible hierarchy format"""
        return [child.to_dict() for child in tree.children]
    
    @staticmethod
    def to_flat_list(tree: TreeNode) -> List[Dict[str, Any]]:
        """Export tree to flat list with hierarchy information"""
        result = []
        
        def traverse(node: TreeNode, indent: int = 0):
            result.append({
                'type': node.node_type,
                'id': node.node_id,
                'code': node.code,
                'name': node.name,
                'complete_name': node.complete_name,
                'amount': node.amount,
                'total_amount': node.total_amount,
                'level': node.level,
                'indent': indent,
                'has_children': bool(node.children),
                'line_count': node.metadata.get('line_count', 0)
            })
            
            for child in node.children:
                traverse(child, indent + 1)
        
        # Start from root children
        for child in tree.children:
            traverse(child)
        
        return result
    
    @staticmethod
    def to_summary(tree: TreeNode) -> Dict[str, Any]:
        """Export tree summary statistics"""
        def count_nodes(node: TreeNode, type_counts: Dict[str, int]):
            if node.node_type != 'root':
                type_counts[node.node_type] = type_counts.get(node.node_type, 0) + 1
            
            for child in node.children:
                count_nodes(child, type_counts)
        
        type_counts = {}
        count_nodes(tree, type_counts)
        
        return {
            'total_amount': tree.total_amount,
            'node_counts': type_counts,
            'max_depth': max((child.level for child in tree.children), default=0),
            'has_data_count': len([n for n in tree.children if n.metadata.get('has_data')])
        }