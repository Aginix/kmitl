# HR Employee Name Search

Makes an employee findable by their [[hr-employee-academic-standing-thailand]] Academic
Standing Title prefix or by full name (title + name), in both the employee picker (M2O
dropdowns) and the Employees list search box, via a hidden search index.

The displayed name itself is no longer prefixed here: [[hr-employee-name-title-kmitl]]
now composes the title into the stored `name`, so `name_get` returns `name` unchanged
(prepending the abbreviation on top would double the title).

## Language

**Academic Standing Name Search (ดัชนีค้นหา)**: A hidden, stored search index
concatenating every Academic Standing Title variant with the matching employee name. It
exists solely so name-search matches a bare title prefix, a bare name, or a full name
(title + name) in a single `ilike`. Not shown in any view. _Avoid_: search field,
keywords
