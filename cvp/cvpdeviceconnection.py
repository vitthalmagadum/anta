# Copyright (c) 2024-2025 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
# ruff: noqa

from __future__ import annotations
from pathlib import Path

import yaml

# Import the inventory models and services
from cloudvision.Connector.grpc_client import GRPCClient, create_query
from cloudvision.Connector.codec import Wildcard

__all__ = ["CvpDeviceConnection"]

class CvpDeviceConnection:
    """
    CvpDeviceConnection provides a client to connect to a CloudVision instance
    and run queries against its datasets.
    """

    def __init__(
        self,
        host: str,
        port: int = 443,
        token_file: str = "token.txt",
        ca_file: str | None = None,
    ):
        """
        Initialize the CvpDeviceConnection.

        Args:
            host: The CloudVision host.
            port: The gRPC port to connect to.
            token_file: Path to the file containing the access token.
            ca_file: Path to the CA certificate file for a secure connection.
        """
        self.server_addr = f"{host}:{port}"
        self.token = Path(token_file).read_text().strip()
        self.token_file = token_file
        self.ca_file = ca_file
        self.ca_cert = Path(ca_file).read_bytes() if ca_file else None
        self.grpc_client = self.get_grpc_client()

    def get_grpc_client(self):
        return GRPCClient(self.server_addr, token=self.token_file, ca=self.ca_file)

    def get_device_version(self, hostname: str) -> dict[str, str] | None:
        """Fetches the EOS version for a specific device.

        This method queries the 'analytics' dataset in CloudVision to find the
        EOS version of a device matching the given hostname.

        Args:
            hostname: The hostname of the device to look up.

        Returns:
            A dictionary containing the 'version' of the device if found,
            otherwise None.
        """
        pathElts = [
            "DatasetInfo",
            "Devices"
        ]
        query = [
            create_query([(pathElts, [])], "analytics")
        ]
        for batch in self.grpc_client.get(query):
            for notif in batch["notifications"]:
                if hostname in notif["updates"]:
                    return {"version": notif["updates"][hostname]["eosVersion"]}

        return None

    def get_lldp_neighbors(self, hostname: str) -> dict:
        """
        Fetch LLDP neighbors for a specific device using a GRPCClient.

        Args:
            device_id: The serial number of the device.

        Returns:
            A dictionary containing LLDP neighbor information.
        """
        path_elts = [
            "Sysdb", "l2discovery", "lldp", "status", "local", Wildcard(),
            "portStatus", Wildcard(), "remoteSystem", Wildcard(),
        ]
        query = [create_query([(path_elts, [])], hostname)]
        result = {}

        try:
            for batch in self.grpc_client.get(query):
                for notif in batch.get("notifications", []):
                    if not notif.get("updates"):
                        continue
                    path_elts = notif["path_elements"]
                    lldp_key = path_elts[7]
                    neighbors = result.get(lldp_key, {})
                    neighbors.update(notif["updates"])
                    result[lldp_key] = neighbors

        except Exception as e:
            print(f"An error occurred while fetching LLDP data: {e}")
        
        # TODO: Need to check for either multiple devices can connected on same port
        op = {"lldpNeighbors": {
                result: {
                    "lldpNeighborInfo": [{
                        "systemName": value["sysName"]["value"]["value"],
                        "neighborInterfaceInfo": {
                            "interfaceId_v2": value["msap"]["portIdentifier"]["portId"]
                        }
                    }]
                }
                for result, value in result.items()
            }
        }
        return op

# def run_apis(hostname: str | None, device_id: str | None) -> None:
#     """Fetch device info using the CvpDeviceConnection class."""
#     if not hostname and not device_id:
#         print("Please provide a hostname or device_id as an argument.")
#         return

#     host = "www.cv-staging.corp.arista.io"
#     token_file = "/home/vitthal/work-anta/anta/token.txt"
#     ca_cert_file = "/home/vitthal/work-anta/anta/cvp-anta.crt"

#     try:
#         # We instantiate the class but don't enter the context, as the methods
#         # will create their own clients.
#         cvp_conn = CvpDeviceConnection(host=host, token_file=token_file, ca_file=ca_cert_file)

#         if hostname:
#             print(f"Looking up version for device: {hostname}")
#             version = cvp_conn.get_device_version(hostname)
#             if version:
#                 output_file = Path(f"{hostname}_version.json")
#                 output_file.write_text(str({"version": version}), encoding="utf-8")
#                 print(f"✅ Found version '{version}'. Saved to {output_file}")
#             else:
#                 print(f"Could not find version for device '{hostname}'.")

#         if device_id:
#             print(f"Fetching LLDP neighbors for device: {device_id}")
#             lldp_data = cvp_conn.get_lldp_neighbors(device_id)
#             if lldp_data:
#                 output_file = Path(f"{device_id}_lldp.json")
#                 # A proper JSON serialization would be needed here.
#                 output_file.write_text(str(lldp_data), encoding="utf-8")
#                 print(f"✅ Found LLDP data. Saved to {output_file}")
#             else:
#                 print(f"No LLDP data found for device '{device_id}'.")

#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")


# if __name__ == "__main__":
#     import sys
#     target_hostname = None
#     target_device_id = None
#     if len(sys.argv) > 1:
#         if sys.argv[1] == '--hostname' and len(sys.argv) > 2:
#             target_hostname = sys.argv[2]
#         elif sys.argv[1] == '--device_id' and len(sys.argv) > 2:
#             target_device_id = sys.argv[2]

#     run_apis(target_hostname, target_device_id)