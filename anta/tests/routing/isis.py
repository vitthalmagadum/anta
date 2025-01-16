# Copyright (c) 2023-2025 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Module related to IS-IS tests."""

# Mypy does not understand AntaTest.Input typing
# mypy: disable-error-code=attr-defined
from __future__ import annotations

from ipaddress import IPv4Address, IPv4Network
from typing import Any, ClassVar, Literal

from pydantic import BaseModel

from anta.custom_types import Interface
from anta.models import AntaCommand, AntaTemplate, AntaTest
from anta.tools import get_value


class VerifyISISNeighborState(AntaTest):
    """Verifies the health of all the IS-IS neighbors.

    Expected Results
    ----------------
    * Success: The test will pass if all IS-IS neighbors are in UP state.
    * Failure: The test will fail if some IS-IS neighbors are not in UP state.
    * Skipped: The test will be skipped if no IS-IS neighbor is found.

    Examples
    --------
    ```yaml
    anta.tests.routing:
      isis:
        - VerifyISISNeighborState:
            
    ```
    """

    categories: ClassVar[list[str]] = ["isis"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show isis neighbors vrf all", revision=1)]

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifyISISNeighborState."""
        self.result.is_success()

        # Verify the IS-IS is configured. If not then skip the test.
        if not (command_output := self.instance_commands[0].json_output["vrfs"]):
            self.result.is_skipped("IS-IS is not configured on device")
            return

        for vrf, vrf_data in command_output.items():
            for isis_instance, instace_data in vrf_data["isisInstances"].items():
                if not (neighbors := instace_data["neighbors"]):
                    continue

                for neighbor in neighbors.values():
                    for adjacencies in neighbor["adjacencies"]:
                        if adjacencies["state"] != "up":
                            self.result.is_failure(f"Instance: {isis_instance} VRF: {vrf} Interface: {adjacencies['interfaceName']} - Session (adjacency) down")


class VerifyISISSpecificNeighborState(AntaTest):
    """Verifies the health of all the neighbors for given IS-IS instance(s).

    Expected Results
    ----------------
    * Success: The test will pass if all IS-IS neighbors are in UP state.
    * Failure: The test will fail if any IS-IS neighbor adjance session is down.
    * Skipped: The test will be skipped if no IS-IS neighbor is found.

    Examples
    --------
    ```yaml
    anta.tests.routing:
      isis:
        - VerifyISISSpecificNeighborState:
            isis_instances:
                - name: 100
                  vrf: default
                - name: 100
                  vrf: MGMT
            
    ```
    """

    categories: ClassVar[list[str]] = ["isis"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show isis neighbors vrf all", revision=1)]

    class Input(AntaTest.Input):
        """Input model for the VerifyBGPExchangedRoutes test."""

        isis_instances: list[ISISInstance]
        """List of IS-IS instance."""

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifyISISSpecificNeighborState."""
        self.result.is_success()

        # Verify the IS-IS is configured. If not then skip the test.
        if not (command_output := self.instance_commands[0].json_output["vrfs"]):
            self.result.is_skipped("IS-IS is not configured on device")
            return
        
        for instance in self.inputs.isis_instances:
            if not (neighbors := get_value(command_output, f"{instance.vrf}..isisInstances..{instance.name}..neighbors", separator="..")):
                self.result.is_failure(f"{instance} - No IS-IS neighbor detected")
                continue

            for neighbor in neighbors.values():
                for adjacencies in neighbor["adjacencies"]:
                    if adjacencies["state"] != "up":
                        self.result.is_failure(f"{instance} Interface: {adjacencies['interfaceName']} - Session (adjacency) down")


class VerifyISISNeighborCount(AntaTest):
    """Verifies number of IS-IS neighbors per level and per interface.

    Expected Results
    ----------------
    * Success: The test will pass if the number of neighbors is correct.
    * Failure: The test will fail if the number of neighbors is incorrect.
    * Skipped: The test will be skipped if no IS-IS neighbor is found.

    Examples
    --------
    ```yaml
    anta.tests.routing:
      isis:
        - VerifyISISNeighborCount:
            isis_instances:
                - name: 100
                  vrf: default
                  local_interfaces:
                    - name: Ethernet1
                      level: 1
                      count: 2
    ```
    """

    categories: ClassVar[list[str]] = ["isis"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show isis interface brief vrf all", revision=1)]

    class Input(AntaTest.Input):
        """Input model for the VerifyISISNeighborCount test."""

        isis_instances: list[ISISInstance]
        """List of IS-IS instance."""
        InterfaceCount: ClassVar[type[ISISInterface]] = ISISInterface

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifyISISNeighborCount."""
        self.result.is_success()

        # Verify the IS-IS is configured. If not then skip the test.
        if not (command_output := self.instance_commands[0].json_output["vrfs"]):
            self.result.is_skipped("IS-IS is not configured on device")
            return

        for instance in self.inputs.isis_instances:
            for interface in instance.local_interfaces:
                if not (interface_detail := get_value(command_output, f"{instance.vrf}..isisInstances..{instance.name}..interfaces..{interface.name}", separator="..")):
                    self.result.is_failure(f"{instance} {interface} - Not configured")
                    continue
                
                act_count = get_value(interface_detail, f"intfLevels.{interface.level}.numAdjacencies")
                if act_count != interface.count:
                    self.result.is_failure(f"{instance} {interface} - Neighbor count mismatch - Expected: {interface.count} Actual: {act_count}")


class VerifyISISInterfaceMode(AntaTest):
    """Verifies ISIS Interfaces are running in correct mode.

    Expected Results
    ----------------
    * Success: The test will pass if all listed interfaces are running in correct mode.
    * Failure: The test will fail if any of the listed interfaces is not running in correct mode.
    * Skipped: The test will be skipped if no ISIS neighbor is found.

    Examples
    --------
    ```yaml
    anta.tests.routing:
      isis:
        - VerifyISISInterfaceMode:
            isis_instances:
                - name: 100
                  vrf: default
                  local_interfaces:
                    - name: Ethernet1
                      level: 1
                      mode: point-to-point
    ```
    """

    categories: ClassVar[list[str]] = ["isis"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show isis interface brief vrf all", revision=1)]

    class Input(AntaTest.Input):
        """Input model for the VerifyISISNeighborCount test."""

        isis_instances: list[ISISInstance]
        """List of IS-IS instance."""
        InterfaceState: ClassVar[type[ISISInterface]] = ISISInterface

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifyISISInterfaceMode."""
        command_output = self.instance_commands[0].json_output
        self.result.is_success()

        # Verify the IS-IS is configured. If not then skip the test.
        if not (command_output := self.instance_commands[0].json_output["vrfs"]):
            self.result.is_skipped("IS-IS is not configured on device")
            return

        for instance in self.inputs.isis_instances:
            for interface in instance.local_interfaces:
                if not (interface_detail := get_value(command_output, f"{instance.vrf}..isisInstances..{instance.name}..interfaces..{interface.name}", separator="..")):
                    self.result.is_failure(f"{instance} {interface} - Not configured")
                    continue

                # Check for passive
                if interface.mode == "passive" and get_value(interface_detail, f"intfLevels.{interface.level}.passive", default=False) is False:
                    self.result.is_failure(f"{instance} {interface} - Not running in passive mode")

                elif interface.mode != (interface_type := get_value(interface_detail, "interfaceType", default="unset")):
                    self.result.is_failure(f"{interface} - Incorrect circuit type - Expected: {interface.mode} Actual: {interface_type}")


class VerifyISISSegmentRoutingAdjacencySegments(AntaTest):
    """Verify that all expected Adjacency segments are correctly visible for each interface.

    Expected Results
    ----------------
    * Success: The test will pass if all listed interfaces have correct adjacencies.
    * Failure: The test will fail if any of the listed interfaces has not expected list of adjacencies.
    * Skipped: The test will be skipped if no ISIS SR Adjacency is found.

    Examples
    --------
    ```yaml
    anta.tests.routing:
      isis:
        - VerifyISISSegmentRoutingAdjacencySegments:
            instances:
              - name: CORE-ISIS
                vrf: default
                segments:
                  - interface: Ethernet2
                    address: 10.0.1.3
                    sid_origin: dynamic
    ```
    """

    categories: ClassVar[list[str]] = ["isis", "segment-routing"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show isis segment-routing adjacency-segments vrf all", ofmt="json")]

    class Input(AntaTest.Input):
        """Input model for the VerifyISISSegmentRoutingAdjacencySegments test."""

        instances: list[IsisInstance]

        class IsisInstance(BaseModel):
            """ISIS Instance model definition."""

            name: str
            """ISIS instance name."""
            vrf: str = "default"
            """VRF name where ISIS instance is configured."""
            segments: list[Segment]
            """List of Adjacency segments configured in this instance."""

            class Segment(BaseModel):
                """Segment model definition."""

                interface: Interface
                """Interface name to check."""
                level: Literal[1, 2] = 2
                """ISIS level configured for interface. Default is 2."""
                sid_origin: Literal["dynamic"] = "dynamic"
                """Adjacency type"""
                address: IPv4Address
                """IP address of remote end of segment."""

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifyISISSegmentRoutingAdjacencySegments."""
        command_output = self.instance_commands[0].json_output
        self.result.is_success()

        # Verify the IS-IS is configured. If not then skip the test.
        if not (command_output := self.instance_commands[0].json_output["vrfs"]):
            self.result.is_skipped("IS-IS is not configured on device")
            return
        
        for instance in self.inputs.isis_instances:
            if not (instance_data := get_value(command_output, f"{instance.vrf}..isisInstances..{instance.name}", separator="..")):
                self.result.is_failure(f"{instance} - Not configured")
                continue

            for input_segment in instance.segments:
                neighbor=str(input_segment.address)
                level = input_segment.level

                adjacency_segment = next((segment for segment in instance_data["adjacencySegments"] if (segment["ipAddress"] == neighbor and segment["level"] == level)), None)
                if adjacency_segment is None:
                    self.result.is_failure(f"{instance} {input_segment} - Not configured")
                    continue

                if (act_origin := adjacency_segment["sidOrigin"]) != input_segment.sid_origin:
                    self.result.is_failure(
                        f"{instance} {input_segment} - Incorrect Segment Identifier origin - Expected: {input_segment.sid_origin} Actual: {act_origin}"
                    )
