# Copyright (c) 2025 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
# Initially written by Jeremy Schulman at https://github.com/jeremyschulman/aio-eapi

from cloudvision.Connector.grpc_client import create_query
from cloudvision.Connector.codec import Wildcard
# ruff: noqa

def get(client, hostname, path_elts):
    """Returns a query on a path element"""
    result = {}
    query = [create_query([(path_elts, [])], hostname)]

    for batch in client.get(query):
        for notif in batch["notifications"]:
            result.update(notif["updates"])
    return result

def device_type(client, hostname):
    """Returns the type of the device: modular/fixed"""
    path_elts = ["Sysdb", "hardware", "entmib"]
    query = get(client, hostname, path_elts)
    if query.get("fixedSystem") is None:
        device_type = "modular"
    else:
        device_type = "fixedSystem"
    return device_type

def get_intf_status_chassis(client, hostname):
    """Returns the interfaces report for a modular device."""
    # Fetch the list of slices/linecards
    path_elts = ["Sysdb", "interface", "status", "eth", "phy", "slice"]
    query = get(client, hostname, path_elts)
    result = {}

    # Go through each linecard and get the state of all interfaces
    for lc in query.keys():
        path_elts = [
            "Sysdb",
            "interface",
            "status",
            "eth",
            "phy",
            "slice",
            lc,
            "intfStatus",
            Wildcard(),
        ]

        query_result = [create_query([(path_elts, [])], hostname)]
        for batch in client.get(query_result):
            for notif in batch["notifications"]:
                if not notif["updates"]:
                    continue
                path_elts = notif["path_elements"]
                intf_key = path_elts[-1]
                intf_val = result.get(intf_key, {})
                intf_val.update(notif["updates"])
                result[intf_key] = intf_val
    intf_status_chassis = {
        interface: {
            "interfaceStatus": "up" if result[interface]["linkStatus"]["Name"] == "linkUp" else result[interface]["linkStatus"]["Name"],
            "lineProtocolStatus": "up" if result[interface]["operStatus"]["Name"] == "intfOperUp" else result[interface]["operStatus"]["Name"],
        }
        for interface in result
    }
    return {"interfaceDescriptions": intf_status_chassis}


def get_intf_status_fixed(client, hostname):
    """Returns the interfaces report for a fixed system device."""
    path_elts = [
        "Sysdb",
        "interface",
        "status",
        "eth",
        "phy",
        "slice",
        "1",
        "intfStatus",
        Wildcard(),
    ]
    query = [create_query([(path_elts, [])], hostname)]
    result = {}
    for batch in client.get(query):
        for notif in batch["notifications"]:
            if not notif["updates"]:
                continue
            path_elts = notif["path_elements"]
            intf_key = path_elts[-1]
            intf_val = result.get(intf_key, {})
            intf_val.update(notif["updates"])
            result[intf_key] = intf_val

    intf_status_fixed = {
        interface: {
            "interfaceStatus": "up" if result[interface]["linkStatus"]["Name"] == "linkUp" else result[interface]["linkStatus"]["Name"],
            "lineProtocolStatus": "up" if result[interface]["operStatus"]["Name"] == "intfOperUp" else result[interface]["operStatus"]["Name"],
        }
        for interface in result
    }
    return {"interfaceDescriptions": intf_status_fixed}
