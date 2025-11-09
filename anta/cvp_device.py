from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from anta.logger import anta_log_exception, exc_to_str
from anta.device import AntaDevice
from anta.models import AntaCommand

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cvp import CvpDeviceConnection

logger = logging.getLogger(__name__)


class CVPDevice(AntaDevice):
    """
    Implementation of AntaDevice for a gRPC querry to CloudVision.

    Attributes
    ----------
    name : str
        Device name.
    """

    def __init__(self, name: str, **kwargs) -> None:
        """
        Instantiate a CVPDevice.

        Args:
            name: Device name.
            **kwargs: Catch all additional keyword arguments.
        """
        test_source=kwargs["test_source"]
        token=kwargs["token"]
        crt_file=kwargs["crt_file"]
        super().__init__(name=name, test_source=test_source, token=token, crt_file=crt_file)

        host = kwargs["cvp_host"]
        self.cvp_client = CvpDeviceConnection(host=host, token_file=token, ca_file=crt_file)

    def is_online(self) -> bool:
        """
        TODO
        """
        pass

    def established(self) -> bool:
        """
        TODO
        """
        pass

    @property
    def _keys(self) -> tuple[Any, ...]:
        """Read-only property to implement hashing and equality for CVPDevice classes."""

    @property
    def api_mapping(self) -> dict[str, str]:
        """Load API mapping"""
        with open("./examples/eos-api-mapping.yaml", "r") as f:
            data = yaml.safe_load(f)
        return data

    async def _collect(self, command: AntaCommand, *, collection_id: str | None = None) -> None:
        """
        Collect command output from CVP.
        """
        logger.info(f"Collecting command '{command.command}' for device {self.name} from CVP")

        try:
            mapping = self.api_mapping
            def run_mapped_method(obj, key, mapping):
                method_name = mapping.get(key)
                method = getattr(obj, method_name)
                return method
            command.output = run_mapped_method(self.cvp_client, command.command, mapping)(hostname=self.name)

        except Exception as e:
            logger.error(f"Failed to collect command '{command.command}' for device {self.name} from CVP: {e}")
            command.errors.append(str(e))

    async def refresh(self) -> None:
        """
        Refresh is not implemented for CVPDevice.
        """
        pass

