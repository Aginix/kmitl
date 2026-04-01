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

    @classmethod
    def for_f4_report(cls):
        """Predefined config for F4 reports (revenue - accounts only)"""
        return cls(
            dimensions=['account'],
            include_empty=False,
            calculate_rollups=True,
            amount_field='balance'
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
        self.indent = 0  # Indent level starting from budget_account

        # Financial data
        self.amount = 0.0
        self.amount_total = 0.0

        # Metadata
        self.metadata = {
            'line_ids': [],
            'line_count': 0,
            'has_data': False,
            'expanded': True,
            'res_model': None,
            'res_id': None,
            'created_at': None,
            'custom_data': {},
            'is_last_level': False,  # Flag to indicate if this is a last-level node
            'unique_suffix': None,  # Unique suffix for last-level nodes
            'description': None,  # Description from budget line
            'reached_account': False  # Flag to indicate if we've reached account dimension
        }

    def add_child(self, child: 'TreeNode') -> 'TreeNode':
        """Add child node and set relationships"""
        child.parent = self
        child.level = self.level + 1

        # Calculate indent based on whether we've reached account dimension
        if self.metadata.get('reached_account', False):
            # If parent has reached account, increment indent
            child.indent = self.indent + 1
        elif child.node_type == 'account':
            # If this child is the account node, start indent at 0
            child.indent = 0
        else:
            # Before reaching account, keep indent at 0
            child.indent = 0

        # Propagate reached_account flag
        if self.metadata.get('reached_account', False) or child.node_type == 'account':
            child.metadata['reached_account'] = True

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
            'key': self._get_unique_key(),
            'id': self.node_id,
            'code': self.code,
            'name': self.name,
            'complete_name': self.complete_name,
            'amount': self.amount,
            'amount_total': self.amount_total,
            'level': self.level,
            'indent': self.indent,  # Add indent for display purposes
            'has_data': self.metadata.get('has_data', False),
            'expanded': self.metadata.get('expanded', True),
            'description': self.metadata.get('description', ''),
            'note': self.metadata.get('note', ''),
        }

        # Add children if requested
        if include_children and self.children:
            if self.node_type == 'activity' and self.level == 1:
                # Second tier activity: priority sort (09, 06 first)
                priority_codes = ['09', '06']
                sorted_children = sorted(self.children, key=lambda c: (
                    (priority_codes.index(c.code[:2]), c.code)
                    if len(c.code) >= 2 and c.code[:2] in priority_codes
                    else (len(priority_codes), c.code)
                ))
            else:
                sorted_children = sorted(self.children, key=lambda c: c.code)
            data['children'] = [
                child.to_dict(include_children=True)
                for child in sorted_children
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
            self.amount_total = self.amount
            return self.amount_total

        total = self.amount
        for child in self.children:
            total += child.calculate_rollups()

        self.amount_total = total
        return total

    def _get_unique_key(self) -> str:
        """Generate unique key based on full hierarchy path"""
        path_parts = []
        current = self
        while current and current.node_type != 'root':
            if current.node_id is not None:
                path_parts.insert(0, f"{current.node_type}_{current.node_id}")
            current = current.parent

        # For last-level nodes, append a unique suffix to ensure uniqueness
        key = "_".join(path_parts) if path_parts else f"{self.node_type}_{self.node_id}"
        if self.metadata.get('is_last_level') and self.metadata.get('unique_suffix'):
            key = f"{key}_{self.metadata['unique_suffix']}"

        return key


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
        self._last_level_counter = 0  # Counter for unique suffixes
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
        for dim_index, dimension in enumerate(self.config.dimensions):
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

            # Check if this is the last dimension
            is_last_dimension = (dim_index == len(self.config.dimensions) - 1)

            # Build hierarchy path for this dimension
            hierarchy_path = self._get_record_hierarchy_path(record)
            current = self._build_dimension_path(
                current, dimension, hierarchy_path, depth, line, is_last_dimension
            )
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
                            records: List, base_depth: int, line,
                            is_last_dimension: bool = False) -> TreeNode:
        """Build path for a dimension through its hierarchy

        Args:
            parent: Parent tree node
            dimension: Dimension name
            records: List of records in hierarchy path
            base_depth: Base depth in tree
            line: Original budget line being processed
            is_last_dimension: True if this is the last dimension level
        """
        current = parent

        for i, record in enumerate(records):
            # For the last level of the last dimension, don't use cache
            # This ensures each leaf node remains separate
            is_last_level = is_last_dimension and (i == len(records) - 1)

            if is_last_level:
                # Always create a new node for the last level with unique suffix
                node = self._create_node(dimension, record, current)
                # Mark as last level and assign unique suffix
                node.metadata['is_last_level'] = True
                self._last_level_counter += 1
                node.metadata['unique_suffix'] = f"line_{self._last_level_counter}"
                current.add_child(node)
                current = node
            else:
                # For non-last levels, use cache as before
                parent_path = self._get_current_path_key(current)
                cache_key = f"{dimension}_{record.id}"
                if parent_path:
                    cache_key = f"{parent_path}_{cache_key}"

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

    def _get_current_path_key(self, node: TreeNode) -> str:
        """Get a unique path key representing the current hierarchy position"""
        path_parts = []
        current = node
        while current and current.node_type != 'root':
            if current.node_id is not None:
                path_parts.insert(0, f"{current.node_type}_{current.node_id}")
            current = current.parent
        return "_".join(path_parts)

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
        })

        # Mark if this is account dimension
        if node_type == 'account':
            node.metadata['reached_account'] = True

        return node

    def _add_line_data(self, node: TreeNode, line):
        """Add line data to a node"""
        amount = self._get_line_amount(line)
        node.amount += amount
        node.metadata['has_data'] = True
        node.metadata['line_count'] += 1
        node.metadata['line_ids'].append(line.id)
        # Store description if available
        if hasattr(line, 'description') and line.description:
            node.metadata['description'] = line.description
        if hasattr(line, 'note') and line.note:
            node.metadata['note'] = line.note

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
        """Export to Odoo-compatible hierarchy format with sorting by code"""
        # Special sorting for root level - prioritize specific codes
        priority_codes = ['09', '06']  # Add more priority codes as needed

        def sort_key(node):
            # Extract first 2 digits of code for priority sorting
            code_prefix = node.code[:2] if len(node.code) >= 2 else node.code

            # Check if this is a priority code
            if code_prefix in priority_codes:
                # Return tuple with priority index first, then code
                return (priority_codes.index(code_prefix), node.code)
            else:
                # Non-priority codes come after priority ones, sorted by code
                return (len(priority_codes), node.code)

        # Sort root level children with special logic
        sorted_children = sorted(tree.children, key=sort_key)

        return [child.to_dict() for child in sorted_children]

    @staticmethod
    def to_flat_list(tree: TreeNode) -> List[Dict[str, Any]]:
        """Export tree to flat list with hierarchy information"""

        priority_codes = ['09', '06']  # Add more priority codes as needed
        def sort_key(node):
            # Extract first 2 digits of code for priority sorting
            code_prefix = node.code[:2] if len(node.code) >= 2 else node.code

            # Check if this is a priority code
            if code_prefix in priority_codes:
                # Return tuple with priority index first, then code
                return (priority_codes.index(code_prefix), node.code)
            else:
                # Non-priority codes come after priority ones, sorted by code
                return (len(priority_codes), node.code)

        result = []

        def traverse(node: TreeNode, indent: int = 0):
            result.append({
                'type': node.node_type,
                'id': node.node_id,
                'code': node.code,
                'name': node.name,
                'complete_name': node.complete_name,
                'amount': node.amount,
                'amount_total': node.amount_total,
                'level': node.level,
                'indent': indent,
                'has_children': bool(node.children),
                'line_count': node.metadata.get('line_count', 0),
                'description': node.metadata.get('description', ''),
                'note': node.metadata.get('note', ''),
            })

            if node.node_type == 'activity' and node.level == 1:
                priority_codes = ['09', '06']
                sorted_children = sorted(node.children, key=lambda c: (
                    (priority_codes.index(c.code[:2]), c.code)
                    if len(c.code) >= 2 and c.code[:2] in priority_codes
                    else (len(priority_codes), c.code)
                ))
            else:
                sorted_children = sorted(node.children, key=lambda c: c.code)
            for child in sorted_children:
                if node.node_type == 'account':
                    traverse(child, indent + 1)
                else:
                    traverse(child, indent)

        sorted_children = sorted(tree.children, key=sort_key)

        # Start from root children
        for child in sorted_children:
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
            'amount_total': tree.amount_total,
            'node_counts': type_counts,
            'max_depth': max((child.level for child in tree.children), default=0),
            'has_data_count': len([n for n in tree.children if n.metadata.get('has_data')])
        }
