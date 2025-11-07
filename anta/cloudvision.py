# Copyright (c) 2023-2025 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""ANTA CloudVision Device Abstraction Module."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Literal

from cvprac.cvp_client import CvpClient

from anta.device import AntaDevice
from anta.models import AntaDataRequest, AntaCVPQuery

if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)


class CloudVisionDevice(AntaDevice):
    """
    Implementation of AntaDevice for CloudVision Portal (CVP).
    """

    def __init__(
        self,
        host: str,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        name: str | None = None,
        tags: set[str] | None = None,
        *,
        disable_cache: bool = False,
    ) -> None:
        """
        Instantiate a CloudVisionDevice.

        Parameters
        ----------
        host
            Device FQDN or IP. This is the CVP host.
        port
            CVP port. Defaults to 443.
        username
            Username to connect to CVP.
        password
            Password to connect to CVP.
        token
            Token to connect to CVP.
        name
            Device name in CVP (serial number).
        tags
            Tags for this device.
        disable_cache
            Disable caching for all commands for this device.
        """
        if host is None:
            message = "'host' is required to create a CloudVisionDevice"
            logger.error(message)
            raise ValueError(message)
        if name is None:
            message = "'name' (device serial number) is required to create a CloudVisionDevice"
            logger.error(message)
            raise ValueError(message)

        super().__init__(name, tags, disable_cache=disable_cache)

        self.host = host
        self.port = port
        self._username = username
        self._password = password
        self._token = token
        self._cvp_client: CvpClient | None = None

    @property
    def _keys(self) -> tuple[Any, ...]:
        """Keys for hashing and equality."""
        return (self.host, self.name)

    async def _collect(self, command: AntaDataRequest, *, collection_id: str | None = None) -> None:
        """Collect device command output from CVP."""
        if not isinstance(command, AntaCVPQuery):
            logger.error(f"Unsupported command type: {type(command)}")
            command.errors.append(f"Unsupported command type: {type(command)}")
            return

        if self._cvp_client is None:
            logger.error("CVP client not initialized for device %s", self.name)
            command.errors.append("CVP client not initialized")
            return

        try:
            method_name = command.query.get("method")
            params = command.query.get("params", {})

            if not method_name:
                raise ValueError("'method' not specified in the CVP query")

            # Get the actual function from the cvp_client
            cvp_api_method = getattr(self._cvp_client.api, method_name, None)

            if not callable(cvp_api_method):
                raise ValueError(f"'{method_name}' is not a valid cvprac API method.")

            logger.debug("Querying CVP with method '%s' and params %s on device %s", method_name, params, self.name)

            # Execute the CVP API call in a separate thread
            result = await asyncio.to_thread(cvp_api_method, **params)
            command.output = result
            logger.debug("CVP query result for %s: %s", self.name, command.output)

        except Exception as e:
            error_message = f"Error collecting data from CVP for device {self.name}: {e}"
            logger.error(error_message)
            command.errors.append(error_message)

    async def refresh(self) -> None:
        """Update attributes of a CloudVisionDevice instance."""
        logger.debug(f"Refreshing device {self.name}")

        if self._username and self._password:
            self._cvp_client = CvpClient()
            await asyncio.to_thread(
                self._cvp_client.connect,
                nodes=[self.host],
                username=self._username,
                password=self._password,
                port=self.port,
            )
        elif self._token:
            self._cvp_client = CvpClient()
            await asyncio.to_thread(
                self._cvp_client.connect,
                nodes=[self.host],
                api_token=self._token,
                port=self.port,
            )
        else:
            self.is_online = False
            self.established = False
            logger.warning(f"No credentials provided for CVP connection to {self.host}")
            return

        self.is_online = True

        try:
            device_info = await asyncio.to_thread(
                self._cvp_client.api.get_device_by_id, self.name
            )
            self.hw_model = device_info.get("modelName")
            self.established = True
        except Exception as e:
            self.established = False
            logger.warning(f"Could not find device {self.name} on CVP {self.host}: {e}")


    async def copy(self, sources: list[Path], destination: Path, direction: Literal["to", "from"] = "from") -> None:
        """File copy is not supported for CloudVisionDevice."""
        _ = (sources, destination, direction)
        msg = f"copy() method has not been implemented in {self.__class__.__name__} definition"
        raise NotImplementedError(msg)
