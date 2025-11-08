from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from anta.logger import anta_log_exception, exc_to_str
from anta.device import AntaDevice
from anta.models import AntaCommand
from cvprac.cvp_client import CvpClient
from cloudvision.Connector.grpc_client import GRPCClient, create_query
from cloudvision.Connector.codec import Wildcard

logger = logging.getLogger(__name__)


class CVPDevice(AntaDevice):
    """
    Implementation of AntaDevice for a device connected to CloudVision.
    """

    def __init__(self, name: str, **kwargs) -> None:
        """
        Instantiate a CVPDevice.

        Args:
            name: Device name.
            cvp_client: An initialized CVP client.
            tags: Tags for this device.
            disable_cache: Disable caching for all commands for this device.
            **kwargs: Catch all additional keyword arguments.
        """
        test_source=kwargs["test_source"]
        token=kwargs["token"]
        crt_file=kwargs["crt_file"]
        super().__init__(name=name, test_source=test_source, token=token, crt_file=crt_file)

        host = kwargs["cvp_host"]
        self.grpc_client = GRPCClient(f"{host}:443", token=token, ca=crt_file)

    # @property
    # def is_online(self) -> bool:
    #     """
    #     Always return True for a CVPDevice.
    #     """
    #     return True

    # @property
    # def established(self) -> bool:
    #     """
    #     Always return True for a CVPDevice.
    #     """
    #     return True

    @property
    def _keys(self) -> tuple[Any, ...]:
        """Read-only property to implement hashing and equality for CVPDevice classes."""

    def _get_device_version(self) -> dict[str, str] | None:
        """Fetches the EOS version for a specific device."""
        pathElts = [
            "DatasetInfo",
            "Devices"
        ]
        query = [
            create_query([(pathElts, [])], "analytics")
        ]
        
        for batch in self.grpc_client.get(query):
            for notif in batch["notifications"]:
                if self.name in notif["updates"]:
                    return {"version": notif["updates"][self.name]["eosVersion"]}
        return None

    async def _collect(self, command: AntaCommand, *, collection_id: str | None = None) -> None:
        """
        Collect device command output from CVP.
        """
        logger.info(f"Collecting command '{command.command}' for device {self.name} from CVP")

        try:
            if command.command == "show version":
                command.output = self._get_device_version()
            else:
                # This is a placeholder for actual command execution logic
                # The path elements and query construction will depend on the command
                path_elts = [
                    "Sysdb", "l2discovery", "lldp", "status", "local", Wildcard(),
                    "portStatus", Wildcard(), "remoteSystem", Wildcard(),
                ]
                query = [create_query([(path_elts, [])], self.name)]
                
                result = {}
                for batch in self.grpc_client.get(query):
                    for notif in batch.get("notifications", []):
                        if not notif.get("updates"):
                            continue
                        path_elts = notif["path_elements"]
                        key = path_elts[7]
                        data = result.get(key, {})
                        data.update(notif["updates"])
                        result[key] = data
                
                command.output = result

        except Exception as e:
            logger.error(f"Failed to collect command '{command.command}' for device {self.name} from CVP: {e}")
            command.errors.append(str(e))

    async def refresh(self) -> None:
        """
        Refresh is not implemented for CVPDevice.
        """
        pass

