# Copyright (c) 2025 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
# ruff: noqa

from __future__ import annotations
from pathlib import Path

# Import the inventory models and services
from cloudvision.Connector.grpc_client import GRPCClient, create_query
from cloudvision.Connector.codec import Wildcard
from .utils import getIntfStatusChassis, getIntfStatusFixed, deviceType

__all__ = ["CvpClient"]

class CvpClient:
    """
        CvpClient provides a client to connect to a CloudVision instance
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
        Initialize the CvpClient.

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
    
    def get_interface_status(self, deviceId):
        interfaceDescriptions = {}
        entmibType = deviceType(self.grpc_client, deviceId)
        if entmibType == "modular":
            interfaceDescriptions.update(getIntfStatusChassis(self.grpc_client, deviceId))
        else:
            interfaceDescriptions.update(getIntfStatusFixed(self.grpc_client, deviceId))

        return(interfaceDescriptions)
