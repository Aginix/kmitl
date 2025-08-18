# BudgetTreeNode - Design and Implementation Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Implementation](#implementation)
5. [Usage Examples](#usage-examples)
6. [Performance Considerations](#performance-considerations)
7. [Export Formats](#export-formats)
8. [Testing](#testing)

## Overview

The `BudgetTreeNode` is a central tree structure model designed to handle hierarchical budget data across different budget models in the KMITL Odoo system. It provides a reusable, in-memory tree structure that can be used for budget appropriations, budget moves, and budget commitments.

### Purpose
- Provide a unified tree structure for all budget-related hierarchical data
- Support multiple dimensions (Activity, Fund, Account, Department, Source)
- Enable efficient data traversal and aggregation
- Support multiple export formats for reporting

### Design Patterns
- **Composite Pattern**: For tree structure management
- **Builder Pattern**: For tree construction from different sources
- **Visitor Pattern**: For tree traversal operations
- **Strategy Pattern**: For different export formats

## Architecture

```
┌─────────────────────────────────────────────┐
│           Client Code (Models)              │
│  (budget.appropriation, budget.move, etc.)  │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│         BudgetTreeNode Service              │
│         (Transient Model)                   │
├─────────────────────────────────────────────┤
│ + create_tree()                             │
│ + get_source_lines()                        │
│ + export_tree()                             │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│           TreeNode Class                    │
│         (In-Memory Object)                  │
├─────────────────────────────────────────────┤
│ - node_type, node_id, code, name           │
│ - parent, children, level                   │
│ - amount, total_amount                      │
│ - metadata                                  │
├─────────────────────────────────────────────┤
│ + add_child()                              │
│ + calculate_rollups()                       │
│ + traverse()                                │
│ + to_dict(), to_flat_list()                │
└─────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│          TreeBuilder Class                  │
├─────────────────────────────────────────────┤
│ + build()                                   │
│ + _process_line()                           │
│ + _get_hierarchy_path()                     │
└─────────────────────────────────────────────┘
```

## Core Components

### 1. BudgetTreeNode (Transient Model)

```python
class BudgetTreeNode(models.TransientModel):
    """
    Transient model for budget tree operations
    Not stored in database - only in-memory processing
    """
    _name = 'budget.tree.node'
    _description = 'Budget Tree Node - Central Tree Structure'
```

**Key Responsibilities:**
- Entry point for tree creation
- Configuration management
- Source data retrieval
- Export coordination

### 2. TreeNode Class (In-Memory)

```python
class TreeNode:
    """
    Lightweight in-memory tree node
    """
```

**Attributes:**
- `node_type`: Type of node (root|activity|fund|account|department|source)
- `node_id`: ID from source record
- `code`: Code/Reference from source
- `name`: Display name
- `amount`: Direct amount at this node
- `total_amount`: Rolled up amount including children
- `children`: List of child TreeNodes
- `parent`: Reference to parent TreeNode
- `metadata`: Dict for additional data
- `level`: Depth in tree (0 for root)

**Methods:**
- `add_child(child_node)`: Add child and set parent reference
- `find_or_create_child()`: Find existing child or create new one
- `calculate_rollups()`: Calculate total amounts from bottom up
- `traverse_preorder(callback)`: Pre-order traversal
- `traverse_postorder(callback)`: Post-order traversal
- `find_nodes(predicate)`: Find all nodes matching predicate
- `get_path()`: Get path from root to this node
- `to_dict()`: Convert to dictionary
- `to_flat_list()`: Convert tree to flat list

### 3. TreeBuilder Class

```python
class TreeBuilder:
    """
    Builder for constructing tree from budget lines
    """
```

**Key Methods:**
- `build(root_node, lines)`: Build tree from budget lines
- `_process_line(root, line)`: Process single line
- `_get_dimension_records(line, dimension)`: Get records for dimension
- `_get_hierarchy_path(record)`: Get full parent path
- `_filter_lines(lines)`: Apply filters from config

## Implementation

### File: `budget_appropriation/models/budget_tree_node.py`

```python
import logging
import json
import time
from datetime import datetime
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BudgetTreeNode(models.TransientModel):
    """
    Transient model for budget tree operations
    Not stored in database - only in-memory processing
    """
    _name = 'budget.tree.node'
    _description = 'Budget Tree Node - Central Tree Structure'
    
    # Configuration Fields
    source_model = fields.Selection([
        ('budget.appropriation', 'Budget Appropriation'),
        ('budget.move', 'Budget Move'),
        ('budget.commitment', 'Budget Commitment'),
    ], string='Source Model', required=True)
    
    source_ids = fields.Char('Source Record IDs')  # JSON array
    config = fields.Text('Tree Configuration', default='{}')
    
    @api.model
    def create_tree(self, source_model, source_ids, config=None):
        """
        Main entry point to create tree structure
        
        Args:
            source_model: String name of source model
            source_ids: List of record IDs to process
            config: Dict with tree configuration
            
        Returns:
            TreeNode: Root node of the tree
        """
        config = config or self._get_default_config()
        
        # Get source lines
        lines = self._get_source_lines(source_model, source_ids)
        
        # Build tree
        tree = TreeNode()  # Root node
        builder = TreeBuilder(self.env, config)
        builder.build(tree, lines)
        
        return tree
    
    def _get_default_config(self):
        """Default tree configuration"""
        return {
            'dimensions': ['activity', 'fund', 'account'],
            'include_empty': False,
            'calculate_rollups': True,
            'max_depth': None,
            'filters': {}
        }
    
    def _get_source_lines(self, source_model, source_ids):
        """Get lines from source model"""
        if source_model == 'budget.appropriation':
            appropriations = self.env['budget.appropriation'].browse(source_ids)
            return appropriations.mapped('line_ids')
        elif source_model == 'budget.move':
            moves = self.env['budget.move'].browse(source_ids)
            return moves.mapped('line_ids')
        elif source_model == 'budget.commitment':
            commitments = self.env['budget.commitment'].browse(source_ids)
            return commitments.mapped('line_ids')
        return self.env['budget.appropriation.line']


class TreeNode:
    """
    Lightweight in-memory tree node
    """
    
    def __init__(self, node_type='root', node_id=None, code='', name='Root'):
        # Identity
        self.node_type = node_type
        self.node_id = node_id
        self.code = code
        self.name = name
        
        # Tree structure
        self.parent = None
        self.children = []
        self.level = 0
        
        # Values
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
        }
    
    def add_child(self, child_node):
        """Add child and set parent reference"""
        child_node.parent = self
        child_node.level = self.level + 1
        self.children.append(child_node)
        return child_node
    
    def find_or_create_child(self, node_type, node_id, code='', name=''):
        """Find existing child or create new one"""
        # Search existing
        for child in self.children:
            if child.node_type == node_type and child.node_id == node_id:
                return child
        
        # Create new
        new_child = TreeNode(node_type, node_id, code, name)
        return self.add_child(new_child)
    
    def calculate_rollups(self):
        """Calculate total amounts from bottom up"""
        if not self.children:
            # Leaf node
            self.total_amount = self.amount
            return self.total_amount
        
        # Branch node - sum children
        total = self.amount
        for child in self.children:
            total += child.calculate_rollups()
        
        self.total_amount = total
        return total
    
    def traverse_preorder(self, callback):
        """Pre-order traversal: process node before children"""
        callback(self)
        for child in self.children:
            child.traverse_preorder(callback)
    
    def traverse_postorder(self, callback):
        """Post-order traversal: process children before node"""
        for child in self.children:
            child.traverse_postorder(callback)
        callback(self)
    
    def find_nodes(self, predicate):
        """Find all nodes matching predicate"""
        results = []
        if predicate(self):
            results.append(self)
        for child in self.children:
            results.extend(child.find_nodes(predicate))
        return results
    
    def get_path(self):
        """Get path from root to this node"""
        path = []
        current = self
        while current:
            path.insert(0, current)
            current = current.parent
        return path
    
    def to_dict(self, include_children=True):
        """Convert to dictionary"""
        data = {
            'type': self.node_type,
            'id': self.node_id,
            'code': self.code,
            'name': self.name,
            'amount': self.amount,
            'total_amount': self.total_amount,
            'level': self.level,
            'metadata': self.metadata.copy()
        }
        
        if include_children and self.children:
            data['children'] = [
                child.to_dict(include_children=True) 
                for child in self.children
            ]
        
        return data
    
    def to_flat_list(self):
        """Convert tree to flat list with hierarchy info"""
        result = []
        
        def add_to_list(node, indent=0):
            result.append({
                'type': node.node_type,
                'id': node.node_id,
                'code': node.code,
                'name': node.name,
                'amount': node.amount,
                'total_amount': node.total_amount,
                'level': node.level,
                'indent': indent,
                'has_children': bool(node.children)
            })
            
            for child in node.children:
                add_to_list(child, indent + 1)
        
        add_to_list(self)
        return result


class TreeBuilder:
    """
    Builder for constructing tree from budget lines
    """
    
    def __init__(self, env, config):
        self.env = env
        self.config = config
        self.node_cache = {}  # Cache for fast lookup
    
    def build(self, root_node, lines):
        """Build tree from budget lines"""
        # Filter lines
        lines = self._filter_lines(lines)
        
        # Process each line
        for line in lines:
            self._process_line(root_node, line)
        
        # Calculate rollups if configured
        if self.config.get('calculate_rollups', True):
            root_node.calculate_rollups()
    
    def _process_line(self, root, line):
        """Process single line and add to tree"""
        current = root
        
        # Process each dimension in order
        for dimension in self.config.get('dimensions', []):
            records = self._get_dimension_records(line, dimension)
            
            # Build path for this dimension
            for record in records:
                cache_key = (dimension, record.id, current.node_id)
                
                if cache_key in self.node_cache:
                    current = self.node_cache[cache_key]
                else:
                    # Create new node
                    node = current.find_or_create_child(
                        node_type=dimension,
                        node_id=record.id,
                        code=getattr(record, 'code', ''),
                        name=record.name
                    )
                    
                    # Store metadata
                    node.metadata['res_model'] = record._name
                    node.metadata['res_id'] = record.id
                    
                    # Cache it
                    self.node_cache[cache_key] = node
                    current = node
        
        # Add amount to leaf node
        current.amount += self._get_line_amount(line)
        current.metadata['has_data'] = True
        current.metadata['line_ids'].append(line.id)
        current.metadata['line_count'] += 1
    
    def _get_dimension_records(self, line, dimension):
        """Get hierarchy records for dimension"""
        if dimension == 'activity':
            return self._get_hierarchy_path(line.activity_analytic_id)
        elif dimension == 'fund':
            return self._get_hierarchy_path(line.fund_analytic_id)
        elif dimension == 'account':
            return self._get_account_hierarchy_path(line.account_id)
        elif dimension == 'department':
            return self._get_hierarchy_path(line.department_analytic_id)
        elif dimension == 'source':
            return self._get_hierarchy_path(line.source_analytic_id)
        return []
    
    def _get_hierarchy_path(self, record):
        """Get full parent path for hierarchical record"""
        if not record:
            return []
        
        path = []
        current = record
        while current:
            path.insert(0, current)
            current = current.parent_id
        return path
    
    def _get_account_hierarchy_path(self, account):
        """Get hierarchy path for budget account"""
        if not account:
            return []
        
        path = []
        current = account
        while current:
            path.insert(0, current)
            current = current.parent_id
        return path
    
    def _get_line_amount(self, line):
        """Get amount from line based on model type"""
        if hasattr(line, 'balance'):
            return line.balance
        elif hasattr(line, 'amount'):
            return line.amount
        elif hasattr(line, 'debit'):
            return line.debit - line.credit
        return 0.0
    
    def _filter_lines(self, lines):
        """Apply filters from config"""
        # Filter zero amounts
        if not self.config.get('include_empty', False):
            lines = lines.filtered(lambda l: self._get_line_amount(l) != 0)
        
        # Apply custom filters
        filters = self.config.get('filters', {})
        if filters:
            for field, value in filters.items():
                lines = lines.filtered(lambda l: getattr(l, field, None) == value)
        
        return lines


class TreeExporter:
    """Export tree to various formats"""
    
    @staticmethod
    def to_json(tree_node, filename=None):
        """Export tree to JSON"""
        data = tree_node.to_dict()
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(json_str)
        
        return json_str
    
    @staticmethod
    def to_csv(tree_node, filename=None):
        """Export tree to CSV (flat structure)"""
        import csv
        from io import StringIO
        
        flat_data = tree_node.to_flat_list()
        
        output = StringIO()
        if flat_data:
            writer = csv.DictWriter(output, fieldnames=flat_data[0].keys())
            writer.writeheader()
            writer.writerows(flat_data)
        
        csv_str = output.getvalue()
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(csv_str)
        
        return csv_str
    
    @staticmethod
    def to_excel(tree_node, filename):
        """Export tree to Excel with formatting"""
        try:
            import xlsxwriter
        except ImportError:
            raise Exception("xlsxwriter is required for Excel export")
        
        workbook = xlsxwriter.Workbook(filename)
        worksheet = workbook.add_worksheet('Budget Tree')
        
        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D7E4BD',
            'border': 1
        })
        
        amount_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })
        
        # Write headers
        headers = ['Level', 'Type', 'Code', 'Name', 'Amount', 'Total Amount']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write data
        flat_data = tree_node.to_flat_list()
        for row_idx, node_data in enumerate(flat_data, start=1):
            indent = '  ' * node_data['indent']
            worksheet.write(row_idx, 0, node_data['level'])
            worksheet.write(row_idx, 1, node_data['type'])
            worksheet.write(row_idx, 2, node_data['code'])
            worksheet.write(row_idx, 3, indent + node_data['name'])
            worksheet.write(row_idx, 4, node_data['amount'], amount_format)
            worksheet.write(row_idx, 5, node_data['total_amount'], amount_format)
        
        # Auto-fit columns
        worksheet.set_column('A:A', 10)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 50)
        worksheet.set_column('E:F', 20)
        
        workbook.close()


class TreeCache:
    """Simple caching for tree structures"""
    
    _cache = {}
    _max_size = 100
    _ttl = 300  # 5 minutes
    
    @classmethod
    def get(cls, key):
        """Get from cache if valid"""
        if key in cls._cache:
            entry = cls._cache[key]
            if time.time() - entry['timestamp'] < cls._ttl:
                return entry['tree']
            else:
                del cls._cache[key]
        return None
    
    @classmethod
    def set(cls, key, tree):
        """Store in cache with timestamp"""
        # Implement LRU if cache is full
        if len(cls._cache) >= cls._max_size:
            oldest_key = min(cls._cache.keys(), 
                           key=lambda k: cls._cache[k]['timestamp'])
            del cls._cache[oldest_key]
        
        cls._cache[key] = {
            'tree': tree,
            'timestamp': time.time()
        }
```

## Usage Examples

### Basic Usage

```python
# Create tree from budget appropriation
tree_service = self.env['budget.tree.node']
root = tree_service.create_tree(
    source_model='budget.appropriation',
    source_ids=[appropriation_id],
    config={
        'dimensions': ['activity', 'fund', 'account'],
        'calculate_rollups': True
    }
)

# Access tree data
print(f"Total amount: {root.total_amount}")
print(f"Number of children: {len(root.children)}")

# Find specific nodes
expense_nodes = root.find_nodes(lambda n: n.node_type == 'account')
```

### Export to File

```python
# Export to JSON
json_data = TreeExporter.to_json(root, 'budget_tree.json')

# Export to CSV
csv_data = TreeExporter.to_csv(root, 'budget_tree.csv')

# Export to Excel
TreeExporter.to_excel(root, 'budget_tree.xlsx')
```

### Integration with F5 Report

```python
class BudgetAppropriationF5Report(models.TransientModel):
    _inherit = 'budget.appropriation.f5.report'
    
    @api.model
    def get_f5_data_using_tree_node(self, appropriation_id):
        """Get F5 data using central tree node"""
        
        # Check cache
        cache_key = f"f5_tree_{appropriation_id}"
        cached_tree = TreeCache.get(cache_key)
        
        if not cached_tree:
            # Create tree
            tree_service = self.env['budget.tree.node']
            root = tree_service.create_tree(
                source_model='budget.appropriation',
                source_ids=[appropriation_id],
                config={
                    'dimensions': ['activity', 'fund', 'account'],
                    'filters': {'balance': ('!=', 0)}
                }
            )
            
            # Cache it
            TreeCache.set(cache_key, root)
        else:
            root = cached_tree
        
        # Convert to F5 format
        return {
            'hierarchy': root.children[0].to_dict() if root.children else {},
            'summary': {
                'total_amount': root.total_amount,
                'node_count': len(root.find_nodes(lambda n: n.amount > 0))
            }
        }
```

### Custom Traversal

```python
# Pre-order traversal
def print_node(node):
    indent = '  ' * node.level
    print(f"{indent}{node.name}: {node.total_amount:,.2f}")

root.traverse_preorder(print_node)

# Post-order traversal for cleanup
def cleanup_node(node):
    # Perform cleanup operations
    pass

root.traverse_postorder(cleanup_node)

# Find path to specific node
target_node = root.find_nodes(lambda n: n.node_id == 123)[0]
path = target_node.get_path()
print(" → ".join([n.name for n in path]))
```

## Performance Considerations

### Memory Usage

The tree structure is kept in memory, so consider:
- Filter out zero-amount lines
- Limit tree depth if needed
- Use caching for repeated access

### Query Optimization

```python
# Prefetch related data
lines = appropriation.line_ids.filtered(lambda l: l.balance != 0)
lines.mapped('activity_analytic_id.parent_id.parent_id')  # Prefetch parents
lines.mapped('fund_analytic_id.parent_id')
lines.mapped('account_id.parent_id')
```

### Caching Strategy

```python
# Use cache for repeated operations
cache_key = f"{source_model}_{','.join(map(str, source_ids))}"
cached = TreeCache.get(cache_key)

if not cached:
    tree = build_tree()
    TreeCache.set(cache_key, tree)
else:
    tree = cached
```

## Export Formats

### JSON Format

```json
{
  "type": "root",
  "id": null,
  "name": "Root",
  "total_amount": 1000000,
  "children": [
    {
      "type": "activity",
      "id": 1,
      "code": "A001",
      "name": "Education Activity",
      "amount": 0,
      "total_amount": 1000000,
      "children": [
        {
          "type": "fund",
          "id": 10,
          "code": "F001",
          "name": "General Fund",
          "total_amount": 1000000,
          "children": []
        }
      ]
    }
  ]
}
```

### CSV Format

```csv
type,id,code,name,amount,total_amount,level,indent,has_children
root,,Root,,0,1000000,0,0,true
activity,1,A001,Education Activity,0,1000000,1,1,true
fund,10,F001,General Fund,0,1000000,2,2,true
account,100,1000,Salary Account,1000000,1000000,3,3,false
```

### Excel Format

| Level | Type     | Code | Name              | Amount      | Total Amount |
|-------|----------|------|-------------------|-------------|--------------|
| 0     | root     |      | Root              | 0           | 1,000,000    |
| 1     | activity | A001 | Education Activity| 0           | 1,000,000    |
| 2     | fund     | F001 | General Fund      | 0           | 1,000,000    |
| 3     | account  | 1000 | Salary Account    | 1,000,000   | 1,000,000    |

## Testing

### Unit Tests

```python
# tests/test_budget_tree_node.py

from odoo.tests import TransactionCase

class TestBudgetTreeNode(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.tree_service = self.env['budget.tree.node']
        
    def test_tree_creation(self):
        """Test basic tree creation"""
        root = TreeNode()
        child1 = root.find_or_create_child('activity', 1, 'A001', 'Activity 1')
        child2 = child1.find_or_create_child('fund', 10, 'F001', 'Fund 1')
        
        self.assertEqual(len(root.children), 1)
        self.assertEqual(child1.parent, root)
        self.assertEqual(child2.level, 2)
    
    def test_rollup_calculation(self):
        """Test rollup calculations"""
        root = TreeNode()
        child1 = root.find_or_create_child('activity', 1, 'A001', 'Activity 1')
        child2 = child1.find_or_create_child('fund', 10, 'F001', 'Fund 1')
        
        child2.amount = 1000
        root.calculate_rollups()
        
        self.assertEqual(root.total_amount, 1000)
        self.assertEqual(child1.total_amount, 1000)
        self.assertEqual(child2.total_amount, 1000)
    
    def test_tree_traversal(self):
        """Test tree traversal methods"""
        root = TreeNode()
        nodes = []
        
        def collect(node):
            nodes.append(node)
        
        root.traverse_preorder(collect)
        self.assertEqual(len(nodes), 1)
```

### Integration Tests

```python
def test_budget_appropriation_tree(self):
    """Test tree creation from budget appropriation"""
    appropriation = self.env['budget.appropriation'].create({
        'name': 'Test Appropriation',
        'budget_type': 'expense',
        # ... other fields
    })
    
    # Add lines
    line1 = self.env['budget.appropriation.line'].create({
        'appropriation_id': appropriation.id,
        'activity_analytic_id': self.activity1.id,
        'fund_analytic_id': self.fund1.id,
        'account_id': self.account1.id,
        'balance': 1000,
    })
    
    # Create tree
    root = self.tree_service.create_tree(
        source_model='budget.appropriation',
        source_ids=[appropriation.id]
    )
    
    self.assertGreater(root.total_amount, 0)
    self.assertTrue(root.children)
```

## File Structure

```
budget_appropriation/
├── models/
│   ├── __init__.py
│   ├── budget_appropriation.py
│   ├── budget_appropriation_line.py
│   ├── budget_appropriation_f5_report.py
│   └── budget_tree_node.py          # Main tree model
├── utils/
│   ├── __init__.py
│   └── tree_helpers.py              # Helper functions
├── tests/
│   ├── __init__.py
│   └── test_budget_tree_node.py     # Unit tests
└── BUDGET_TREE.md                    # This documentation
```

## Benefits

1. **Reusability**: Single implementation for all budget models
2. **Flexibility**: Configuration-driven dimensions and filters
3. **Performance**: In-memory processing with caching
4. **Exportability**: Multiple export formats (JSON, CSV, Excel)
5. **Maintainability**: Clear separation of concerns
6. **Testability**: Pure Python classes easy to test
7. **Scalability**: Handles large hierarchies efficiently

## Future Enhancements

1. **Lazy Loading**: Load children on demand for large trees
2. **Incremental Updates**: Update tree without full rebuild
3. **Parallel Processing**: Process large datasets in parallel
4. **Visualization**: D3.js integration for tree visualization
5. **API Endpoints**: REST API for tree data access
6. **Real-time Updates**: WebSocket support for live updates

---

*Last Updated: 2024*
*Version: 1.0.0*
*Author: KMITL Development Team*