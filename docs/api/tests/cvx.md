---
anta_title: ANTA Tests for CVX
---

<!--
  ~ Copyright (c) 2023-2025 Arista Networks, Inc.
  ~ Use of this source code is governed by the Apache License 2.0
  ~ that can be found in the LICENSE file.
  -->

## Tests

::: anta.tests.cvx

    options:
      extra:
          anta_hide_test_module_description: true
      filters:
        - "!test"
        - "!render"
        - "!^_[^_]"
        - "!mcs_path_types"
      heading_level: 3
      merge_init_into_class: false
      show_bases: false
      show_labels: true
      show_root_heading: false
      show_root_toc_entry: false
      show_symbol_type_heading: false
      show_symbol_type_toc: false

## Input models

::: anta.input_models.cvx

    options:
      extra:
          anta_hide_test_module_description: true
      filters:
        - "!test"
        - "!render"
      heading_level: 3
      merge_init_into_class: false
      show_bases: false
      show_labels: true
      show_root_heading: false
      show_root_toc_entry: false
      show_symbol_type_heading: false
      show_symbol_type_toc: false
