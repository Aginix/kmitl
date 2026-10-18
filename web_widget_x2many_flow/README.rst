==============================
Web Widget X2many Flow Diagram
==============================

Adds the ``x2many_flow`` field widget: a one2many drawn as a flow diagram of
cards instead of a table. Lines are stacked in **Layers** by a numeric field
(``sequence``, ``order``, ...); lines sharing the same value sit side by side in
one Layer, joined to the next Layer by a fork/join connector.

* Vertical or horizontal layout, switchable per user (remembered in the browser;
  small screens are always vertical).
* Drag a card onto a Layer to join it, or between Layers to start a new one.
  Only the Layers after the drop point are renumbered.
* ``Add`` creates a line in a new last Layer, ``+`` next to a Layer creates one
  inside it — both open the standard x2many dialog (the sub ``<form>``).
* The gear on a card opens the line; the trash icon removes it.

Usage
=====

Add the widget to a one2many that has a ``<tree>`` (it supplies the card
content) and preferably a ``<form>`` (the create / edit dialog)::

    <field name="line_ids" widget="x2many_flow"
           options="{'order_field': 'sequence',
                     'direction': 'horizontal',
                     'title_field': 'name',
                     'card_fields': ['user_id', 'state'],
                     'card_width': '22rem'}">
        <tree decoration-success="state == 'done'">
            <field name="sequence" attrs="{'readonly': [('state', '=', 'done')]}"/>
            <field name="name"/>
            <field name="user_id"/>
            <field name="state" widget="badge"/>
        </tree>
        <form>...</form>
    </field>

Options (all optional):

``order_field``
    The Layer Key. Defaults to the tree's ``widget="handle"`` field, then
    ``sequence``, then ``order``. Must be an Integer or Float column of the tree.
``direction``
    ``vertical`` (default) or ``horizontal`` — the initial layout.
``title_field``
    Card title column; defaults to the first visible column.
``card_fields``
    Columns shown on the card body; defaults to every visible column except
    those marked ``optional="hide"``. Empty values are not shown.
``card_width``
    Card width: a number of pixels (``320``) or any CSS length (``'22rem'``).
    Defaults to ``280px``.

A ``readonly`` modifier on the Layer Key column **locks** that line: it cannot
be dragged, pushed by another drop, or removed from its card. A first Layer
holding a locked line is **anchored**: nothing can join it, be added to it or
be placed before it. ``decoration-*`` on the ``<tree>`` colours the card's
left stripe.

Write the ``<tree>`` inside the field (or set ``mode="tree"``). Without an
inline tree, Odoo loads a kanban sub-view on small screens and the widget
shows an error instead of the diagram.

See ``CONTEXT.md`` for the vocabulary and ``docs/adr/`` for design decisions.
