# Copyright (c) 2023-2025 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.

cvp_eapi_mapping = {
    "show interfaces description": "get_interface_status",
    "show version": "get_device_version",
    "show lldp neighbors detail": "get_lldp_neighbors",
}
