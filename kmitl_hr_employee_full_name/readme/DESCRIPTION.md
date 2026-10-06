Splits the employee display **Name** into structured parts — a **Prefix**,
**Firstname**, **Middlename** and **Lastname** — plus a **secondary** set of the same
parts for an alternate-language name (with a computed combined `name_secondary`).

Key behaviour:

- The display **Name** is kept in sync with the name parts on create and write, and a
  typed **Name** is reverse-parsed back into the individual parts.
- A **Prefix** master model (`hr.employee.prefix`) provides a maintainable list of
  prefixes, managed under **Employees → Configuration → Prefixes**.
- Employee search matches on both the primary and the secondary name.
- The name fields are exposed read-only on the public employee model.
- When `partner_firstname` is installed, the name parts are propagated to the related
  partner. On install, existing employees' names are split into parts automatically.
