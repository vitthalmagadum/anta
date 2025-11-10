# Copyright (c) 2025 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
# Initially written by Jeremy Schulman at https://github.com/jeremyschulman/aio-eapi

from cloudvision.Connector.grpc_client import create_query
from cloudvision.Connector.codec.custom_types import FrozenDict
from cloudvision.Connector.codec import Wildcard
# ruff: noqa

def get(client, dataset, pathElts):
    """Returns a query on a path element"""
    result = {}
    query = [create_query([(pathElts, [])], dataset)]

    for batch in client.get(query):
        for notif in batch["notifications"]:
            result.update(notif["updates"])
    return result


def unfreeze(o):
    """Used to unfreeze Frozen dictionaries"""
    if isinstance(o, (dict, FrozenDict)):
        return dict({k: unfreeze(v) for k, v in o.items()})

    if isinstance(o, (str)):
        return o

    try:
        return [unfreeze(i) for i in o]
    except TypeError:
        pass

    return o

def deviceType(client, dId):
    """Returns the type of the device: modular/fixed"""
    pathElts = ["Sysdb", "hardware", "entmib"]
    dataset = dId
    query = get(client, dataset, pathElts)
    query = unfreeze(query)
    if query["fixedSystem"] is None:
        dType = "modular"
    else:
        dType = "fixedSystem"
    return dType

def getIntfStatusChassis(client, dId):
    """Returns the interfaces report for a modular device."""
    # Fetch the list of slices/linecards
    pathElts = ["Sysdb", "interface", "status", "eth", "phy", "slice"]
    dataset = dId
    query = get(client, dataset, pathElts)
    queryLC = unfreeze(query).keys()
    intfStatusChassis = {}
    result = {}

    # Go through each linecard and get the state of all interfaces
    for lc in queryLC:
        pathElts = [
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

        query = [create_query([(pathElts, [])], dataset)]
        for batch in client.get(query):
            for notif in batch["notifications"]:
                if not notif["updates"]:
                    continue
                path_elts = notif["path_elements"]
                intf_key = path_elts[-1]
                intf_val = result.get(intf_key, {})
                intf_val.update(notif["updates"])
                result[intf_key] = intf_val
    for interface in result:
        intfStatusChassis.update(
            {
                interface["path_elements"][-1]:
                    {
                        "interfaceStatus": "up" if interface["updates"]["linkStatus"]["Name"] == "linkUp" else interface["updates"]["linkStatus"]["Name"],
                        "lineProtocolStatus": "up" if interface["updates"]["operStatus"]["Name"] == "intfOperUp" else interface["updates"]["operStatus"]["Name"],
                    }
            }
        )
    return {"interfaceDescriptions": intfStatusChassis}


def getIntfStatusFixed(client, dId):
    """Returns the interfaces report for a fixed system device."""
    pathElts = [
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
    query = [create_query([(pathElts, [])], dId)]
    query = unfreeze(query)
    result = {}
    intfStatusFixed = {}
    for batch in client.get(query):
        for notif in batch["notifications"]:
            if not notif["updates"]:
                continue
            path_elts = notif["path_elements"]
            intf_key = path_elts[-1]
            intf_val = result.get(intf_key, {})
            intf_val.update(notif["updates"])
            result[intf_key] = intf_val

    for interface in result:
        intfStatusFixed.update(
            {
                interface:
                    {
                        "interfaceStatus": "up" if result[interface]["linkStatus"]["Name"] == "linkUp" else result[interface]["linkStatus"]["Name"],
                        "lineProtocolStatus": "up" if result[interface]["operStatus"]["Name"] == "intfOperUp" else result[interface]["operStatus"]["Name"],
                    },
            }
        )
    return {"interfaceDescriptions": intfStatusFixed}
