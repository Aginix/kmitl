# HR Employee Name Search

Makes an employee findable by their [[hr-employee-academic-standing-thailand]] Academic
Standing Title prefix or by full name (title + name), in both the employee picker (M2O
dropdowns) and the Employees list search box.

## Language

**Full Name (ชื่อเต็ม)**: The Academic Standing Title glued to the employee's name (e.g.
`ศ.ดร. สมชาย ใจดี`) — the value shown in the employee picker and the thing a user types
to find someone. Thai titles pair with the Thai name, English titles with the English
name (`name_secondary`). _Avoid_: display name, complete name

**Academic Standing Name Search (ดัชนีค้นหา)**: A hidden, stored search index
concatenating every Academic Standing Title variant with the matching employee name. It
exists solely so name-search matches a bare title prefix, a bare name, or a full name
(title + name) in a single `ilike`. Not shown in any view. _Avoid_: search field,
keywords
