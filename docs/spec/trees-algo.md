This module contains the parsing of a set of rules into an abstract syntax tree.

- Each rule in a sharing CSV sheet can only reference rules defined in a
  previous row.
- a node has a type/kind, a value, and a list of children
- the children of a node is called 'sons' since it's shorter
- nodes are first added to ctx and then later added to parent nodes with O(1)
  lookup, this way the tree is constructed incrementally while parsing each
  rule
- share nodes are made to be children of a single root-node, since each org
  gets its own node, there may be multiple share-rules, and the tree
  can only have a single root node
- the root-node is updated every time a new share-node is added
- tables of each rule are cached for O(1) lookup

Algorithm:

for each rule:
    for each table in rule, or just once if no table:
        init node, depending on rule mode:
            select:
                kind = select
                value = empty if sons are specified, otherwise 'all'
                sons = a value node for each column name
            filter:
                kind = filter
                value = operator
                sons =
                    1. a key node for the field name
                    2. a value node for each filter value
            group:
                kind = group
                value = operator
                sons = nodes matching the rule's list of ids
            share:
                kind = root
                sons =
                    for each organization:
                        kind = share
                        value = org
                        sons =
                            for each select-node referenced in share-rule:
                                for each table in select-node's rule:
                                    kind = "table"
                                    value = table
                                    sons =
                                        1. select node
                                        2. filter/group node referenced in
                                           share-node. Multiple nodes are
                                           implicitly grouped with an AND-node.
