class BudgetNode:
    def __init__(self, value, node_type):
        self.value = value
        self.node_type = node_type
        self.children = []

        # Transaction Data
        self.lines = []

    def add_child(self, node):
        self.children.append(node)

    def add_line(self, line):
        self.lines.append(line)

    def to_dict(self):
        return {
            "appropriation": self.appropriation(),
            "commitment": self.commitment(),
            "obligation": self.obligation(),
            "expenditure": self.expenditure(),
            "total_balance": self.total_balance(),
            "total_expenditure": self.total_expenditure(),
            "return_unspend": self.return_unspend(),
            "id": self.value["id"],
            "code": self.value["code"],
            "name": self.value["name"],
            "type": self.node_type,
            "parent_id": self.value["parent_id"],
            "parent_path": self.value["parent_path"],
            "node_level": self.value["node_level"],
            "children": list(map(lambda child: child.to_dict(), self.children)),
            "lines": self.lines,
        }

    def appropriation(self):
        total = 0
        for record in self.children:
            total += record.appropriation()
        for line in self.lines:
            if line["model"] == "budget.move.line":
                if line.get("move_type") in ["appropriation", "entry"]:
                    total += line["balance"]
        return total

    def commitment(self):
        """(b) จองเงิน = sum(reserve) - sum(obligate) — reserved, not yet obligated"""
        total = 0
        for record in self.children:
            total += record.commitment()
        reserve_total = 0
        obligate_total = 0
        for line in self.lines:
            if line["model"] == "budget.commitment.line":
                if line["move_type"] == "reserve":
                    reserve_total += line["balance"]
                elif line["move_type"] == "obligate":
                    obligate_total += line["balance"]
        total += reserve_total - obligate_total
        return total

    def obligation(self):
        """(c) ผูกพัน = sum(obligate) - sum(consume) — obligated, not yet consumed"""
        total = 0
        for record in self.children:
            total += record.obligation()
        obligate_total = 0
        consume_total = 0
        for line in self.lines:
            if line["model"] == "budget.commitment.line":
                if line["move_type"] == "obligate":
                    obligate_total += line["balance"]
                elif line["move_type"] == "consume":
                    consume_total += line["balance"]
        total += obligate_total - consume_total
        return total

    def expenditure(self):
        """(d) เบิกจ่ายแล้ว = sum(consume) from commitment lines"""
        total = 0
        for record in self.children:
            total += record.expenditure()
        for line in self.lines:
            if line["model"] == "budget.commitment.line":
                if line["move_type"] == "consume":
                    total += line["balance"]
        return total

    def total_balance(self):
        return self.appropriation() - self.total_expenditure()

    def total_expenditure(self):
        return self.commitment() + self.obligation() + self.expenditure()

    def return_unspend(self):
        return 0

    def has_descendant(self):
        if self.children:
            return True

        for child in self.children:
            if child.has_descendant():
                return True

        return False


class BudgetTree:
    def __init__(
        self,
        accounts=None,
        move_lines=None,
        commitment_lines=None,
        activities=None,
        funds=None,
        sources=None,
        departments=None,
    ):
        self.root = []
        self.rows = []
        self.accounts = accounts
        self.activities = activities
        self.funds = funds
        self.sources = sources
        self.departments = departments
        self.move_lines = move_lines
        self.commitment_lines = commitment_lines

    def _prepare_node(self, record, node_type=None):
        path_ids = record.parent_path.split("/")
        return BudgetNode(
            value={
                "id": record.id,
                "code": record.code,
                "name": record.name,
                "root_id": path_ids[0],
                "parent_id": record.parent_id.id,
                "parent_path": record.parent_path,
                "node_level": len(path_ids) - 1,
            },
            node_type=node_type,
        )

    def _prepare_line(self, line, model=None):
        data = {
            "id": line.id,
            "code": line.account_id.code,
            "name": line.account_id.name,
            "account_id": line.account_id.id,
            "model": model,
            "activity_analytic_id": line.activity_analytic_id.id,
            "department_analytic_id": line.department_analytic_id.id,
            "fund_analytic_id": line.fund_analytic_id.id,
            "source_analytic_id": line.source_analytic_id.id,
        }

        if model == "budget.move.line":
            data["budget_type"] = line.budget_type
            data["move_type"] = line.move_id.move_type
            data["state"] = line.parent_state
            data["balance"] = line.balance
            data["credit"] = line.credit
            data["debit"] = line.debit
        elif model == "budget.commitment.line":
            data["move_type"] = line.move_type
            data["state"] = line.state
            data["balance"] = line.amount

        return data

    def _build_tree(self, node_type=None):
        data = []
        if node_type == "account":
            data = self.accounts
        elif node_type == "activity":
            data = self.activities
        elif node_type == "fund":
            data = self.funds
        elif node_type == "source":
            data = self.sources
        elif node_type == "department":
            data = self.departments

        nodes = dict(
            (record.id, self._prepare_node(record, node_type=node_type))
            for record in data
        )
        for record in data:
            if record.parent_id.id:
                nodes[record.parent_id.id].add_child(nodes.get(record.id))
        return nodes

    def build_tree(self, dimensions=None):
        """
        สร้าง tree ตาม dimensions ที่กำหนด
        dimensions สามารถเป็น:
        - None หรือ [] = ["account"] (default)
        - ["activity"] = แค่ activity hierarchy
        - ["department"] = แค่ department hierarchy
        - ["activity", "account"] = activity -> account
        - ["department", "fund", "account"] = department -> fund -> account
        """
        if not dimensions:
            dimensions = ["account"]  # default

        def get_dimension_id(record, dimension):
            if dimension == "activity":
                return record.activity_analytic_id.id
            elif dimension == "department":
                return record.department_analytic_id.id
            elif dimension == "fund":
                return record.fund_analytic_id.id
            elif dimension == "source":
                return record.source_analytic_id.id
            elif dimension == "account":
                return record.account_id.id
            return None

        # Prepare move lines
        move_line_map = dict(
            (record.id, self._prepare_line(record, model="budget.move.line"))
            for record in self.move_lines
        )

        # Prepare commitment lines
        commitment_line_map = dict(
            (record.id, self._prepare_line(record, model="budget.commitment.line"))
            for record in self.commitment_lines
        )

        # กรณี 1 มิติ
        if len(dimensions) == 1:
            dim = dimensions[0]
            mapped = self._build_tree(dim)

            # Add move lines
            for move_line in self.move_lines:
                node_id = get_dimension_id(move_line, dim)
                if node_id and node_id in mapped:
                    mapped[node_id].add_line(move_line_map[move_line.id])

            # Add commitment lines
            for commitment_line in self.commitment_lines:
                node_id = get_dimension_id(commitment_line, dim)
                if node_id and node_id in mapped:
                    mapped[node_id].add_line(commitment_line_map[commitment_line.id])

            return [n for n in mapped.values() if n.value["parent_id"] is False]

        # กรณีหลายมิติ
        return self._build_multi_dimension_chain(
            dimensions, get_dimension_id, move_line_map, commitment_line_map
        )

    def _build_multi_dimension_chain(self, dimensions, get_dimension_id, move_line_map, commitment_line_map):
        """สร้าง hierarchical tree ที่ถูกต้องสำหรับ multi-dimensions"""

        # สร้าง tree สำหรับ dimension แรก (root level)
        root_dim = dimensions[0]
        root_nodes = self._build_tree(root_dim)

        # Cache สำหรับเก็บ unique node combinations
        node_cache = {}

        # Helper function to create dimension data map
        dimension_data = {
            'account': self.accounts,
            'activity': self.activities,
            'fund': self.funds,
            'source': self.sources,
            'department': self.departments
        }

        # Process move lines
        for move_line in self.move_lines:
            self._add_line_to_tree(
                move_line,
                dimensions,
                get_dimension_id,
                root_nodes,
                node_cache,
                dimension_data,
                move_line_map[move_line.id]
            )

        # Process commitment lines
        for commitment_line in self.commitment_lines:
            self._add_line_to_tree(
                commitment_line,
                dimensions,
                get_dimension_id,
                root_nodes,
                node_cache,
                dimension_data,
                commitment_line_map[commitment_line.id]
            )

        return [n for n in root_nodes.values() if n.value["parent_id"] is False]

    def _add_line_to_tree(self, line, dimensions, get_dimension_id, root_nodes,
                          node_cache, dimension_data, line_data):
        """Add a line to the appropriate node in the tree"""

        parent_node = None
        path_key = ""

        for i, dim in enumerate(dimensions):
            dim_id = get_dimension_id(line, dim)
            if not dim_id:
                return  # Skip if dimension ID is missing

            # Build unique path key for this node
            path_key = f"{path_key}/{dim}:{dim_id}" if path_key else f"{dim}:{dim_id}"

            # Check if this node combination already exists
            if path_key not in node_cache:
                if i == 0:
                    # First dimension - use existing root node
                    if dim_id in root_nodes:
                        node_cache[path_key] = root_nodes[dim_id]
                    else:
                        continue
                else:
                    # Create new node for this unique combination
                    original_data = None
                    for record in dimension_data[dim]:
                        if record.id == dim_id:
                            original_data = record
                            break

                    if not original_data:
                        continue

                    # Create new node
                    new_node = self._prepare_node(original_data, node_type=dim)
                    node_cache[path_key] = new_node

                    # Add as child of parent
                    if parent_node:
                        # Check if this node already exists as child
                        existing_child = None
                        for child in parent_node.children:
                            if child.value["id"] == new_node.value["id"] and child.node_type == dim:
                                existing_child = child
                                break

                        if existing_child:
                            node_cache[path_key] = existing_child
                        else:
                            parent_node.add_child(new_node)

            parent_node = node_cache.get(path_key)

            # Add line to the last dimension node
            if i == len(dimensions) - 1 and parent_node:
                parent_node.add_line(line_data)
