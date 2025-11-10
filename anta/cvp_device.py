# Copyright (c) 2025 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""ANTA CVP Device Module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from anta.device import AntaDevice

if TYPE_CHECKING:
    from pathlib import Path

    from anta.models import AntaCommand

logger = logging.getLogger(__name__)


class CVPDevice(AntaDevice):
    """Implementation of AntaDevice to gRPC query to CloudVision.

    Attributes
    ----------
    cvp_host: str
        CloudVision instance hostname.
    token_file: Path
        Path to the access token file.
    ca_file: Path
        Path to the Certificate file.
    name : str
        Device name.
    """

    def __init__(self, cvp_host: str, token_file: Path, crt_file: Path, name: str, test_source: str) -> None:
        """Instantiate a CVPDevice.

        Args:
            cvp_host: CloudVision instance hostname.
            token_file: Path to the access token file.
            crt_file: Path to the Certificate file.
            name : Device name.
        """
        self.cvp_host = cvp_host
        self.token_file = token_file
        self.crt_file = crt_file
        self.name = name
        self.test_source = test_source
        # Initialize the AntaDevice
        super().__init__(name=self.name, test_source=self.test_source)

    @property
    def _keys(self) -> tuple[Any, ...]:
        """Read-only property to implement hashing and equality for CVPDevice classes."""

    async def _collect(self, command: AntaCommand, *, collection_id: str | None = None) -> None:
        """Collect the response of gRPC queryd from CVP.

        Uses the mapping of AntaCommand with the CVP endpoint.

        Parameters
        ----------
        command
            The command to collect.
        collection_id
            str
        """
        msg = f"Collecting command '{command.command}' for device {self.name} from CVP"
        logger.info(msg)

        try:
            # Placeholder for CVPClient
            pass

        except Exception as e:  # noqa: BLE001
            msg = f"Failed to collect command '{command.command}' for device '{self.name}' from CVP: {e}"
            logger.error(msg)
            command.errors.append(str(e))

    async def refresh(self) -> None:
        """TODO: Determine whether device onboarding status needs to be checked."""
