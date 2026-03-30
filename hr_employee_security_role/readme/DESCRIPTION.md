Splits the default Odoo HR **Officer** role into two tiers:

- **Department Officer** – can only view employees within the same master department.
- **Central Office Staff** – can manage (read/write/create/delete) all employees across
  departments.

The HR Manager role automatically inherits Central Office Staff permissions. The module
also restricts the chatter and HR configuration menu to Central Office Staff and above.
