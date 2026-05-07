BASE_FILTER_TEMPLATE="""
views:
  - type: table
    name: Notes
    filters:
      or:
        - and:
            - '!file.inFolder("{folder}")'
            - file.tags.containsAny({filters})
            - '!file.inFolder("{folder}/openspec")'
        - and:
            - file.inFolder("{folder}")
            - '!file.name.endsWith(".base")'
            - file.name != "{name}"
            - '!file.inFolder("{folder}/openspec")'
    order:
      - date
      - file.name
      - about
    sort:
      - property: date
        direction: ASC
"""

MOC_TEMPLATE="""
### Notes
![[{name}.base]]
"""
