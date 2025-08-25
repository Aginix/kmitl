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
                total += line["debit"] if line["debit"] else 0
        return total

    def commitment(self):
        total = 0
        for record in self.children:
            total += record.commitment()
        for line in self.lines:
            if line["model"] == "budget.commitment" and line["state"] == "reserved":
                total += line["balance"]
        return total

    def obligation(self):
        total = 0
        for record in self.children:
            total += record.commitment()
        for line in self.lines:
            if line["model"] == "budget.commitment" and line["state"] == "obligated":
                total += line["balance"]
        return total

    def expenditure(self):
        total = 0
        for record in self.children:
            total += record.expenditure()
        for line in self.lines:
            if line["model"] == "budget.move.line" and line["move_type"] == "consume":
                total += line["credit"] if line["credit"] else 0
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
        elif model == "budget.commitment":
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

        move_line_map = dict(
            (record.id, self._prepare_line(record, model="budget.move.line"))
            for record in self.move_lines
        )

        # กรณี 1 มิติ - ใช้โค้ดเดิม
        if len(dimensions) == 1:
            dim = dimensions[0]
            mapped = self._build_tree(dim)
            for move_line in self.move_lines:
                node_id = get_dimension_id(move_line, dim)
                if node_id and node_id in mapped:
                    mapped[node_id].add_line(move_line_map[move_line.id])

            return [n for n in mapped.values() if n.value["parent_id"] is False]

        # กรณีหลายมิติ - สร้าง chain
        return self._build_multi_dimension_chain(
            dimensions, get_dimension_id, move_line_map
        )

    def _build_multi_dimension_chain(self, dimensions, get_dimension_id, move_line_map):
        """สร้าง chain แบบ dynamic"""

        # สร้าง tree แต่ละมิติแยกกัน
        dimension_trees = {}
        for dim in dimensions:
            dimension_trees[dim] = self._build_tree(dim)

        # เชื่อม chain ตาม order ที่กำหนด
        for move_line in self.move_lines:
            previous_node = None

            for i, dim in enumerate(dimensions):
                node_id = get_dimension_id(move_line, dim)

                if node_id and node_id in dimension_trees[dim]:
                    current_node = dimension_trees[dim][node_id]

                    # เชื่อม chain
                    if previous_node and current_node not in previous_node.children:
                        previous_node.add_child(current_node)

                    # เพิ่ม line ที่ node สุดท้าย
                    if i == len(dimensions) - 1:
                        current_node.add_line(move_line_map[move_line.id])

                    previous_node = current_node

        # return root dimension
        root_dim = dimensions[0]
        return [
            node
            for node in dimension_trees[root_dim].values()
            if node.value["parent_id"] is False
        ]
