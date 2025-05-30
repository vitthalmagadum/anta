# Copyright (c) 2023-2025 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""ANTA runner module."""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from typing_extensions import deprecated

from anta import GITHUB_SUGGESTION
from anta._runner import AntaRunFilters, AntaRunner
from anta.logger import anta_log_exception, exc_to_str
from anta.tools import Catchtime, cprofile

if TYPE_CHECKING:
    from collections.abc import Coroutine

    from anta.catalog import AntaCatalog, AntaTestDefinition
    from anta.device import AntaDevice
    from anta.inventory import AntaInventory
    from anta.result_manager import ResultManager
    from anta.result_manager.models import TestResult

if os.name == "posix":
    import resource

    DEFAULT_NOFILE = 16384

    @deprecated("This function is deprecated and will be removed in ANTA v2.0.0. Use AntaRunner class instead.", category=DeprecationWarning)
    def adjust_rlimit_nofile() -> tuple[int, int]:
        """Adjust the maximum number of open file descriptors for the ANTA process.

        The limit is set to the lower of the current hard limit and the value of the ANTA_NOFILE environment variable.

        If the `ANTA_NOFILE` environment variable is not set or is invalid, `DEFAULT_NOFILE` is used.

        Returns
        -------
        tuple[int, int]
            The new soft and hard limits for open file descriptors.
        """
        try:
            nofile = int(os.environ.get("ANTA_NOFILE", DEFAULT_NOFILE))
        except ValueError as exception:
            logger.warning("The ANTA_NOFILE environment variable value is invalid: %s\nDefault to %s.", exc_to_str(exception), DEFAULT_NOFILE)
            nofile = DEFAULT_NOFILE

        limits = resource.getrlimit(resource.RLIMIT_NOFILE)
        logger.debug("Initial limit numbers for open file descriptors for the current ANTA process: Soft Limit: %s | Hard Limit: %s", limits[0], limits[1])
        nofile = min(limits[1], nofile)
        logger.debug("Setting soft limit for open file descriptors for the current ANTA process to %s", nofile)
        try:
            resource.setrlimit(resource.RLIMIT_NOFILE, (nofile, limits[1]))
        except ValueError as exception:
            logger.warning("Failed to set soft limit for open file descriptors for the current ANTA process: %s", exc_to_str(exception))
        return resource.getrlimit(resource.RLIMIT_NOFILE)


logger = logging.getLogger(__name__)


@deprecated("This function is deprecated and will be removed in ANTA v2.0.0. Use AntaRunner class instead.", category=DeprecationWarning)
def log_cache_statistics(devices: list[AntaDevice]) -> None:
    """Log cache statistics for each device in the inventory.

    Parameters
    ----------
    devices
        List of devices in the inventory.
    """
    for device in devices:
        if device.cache_statistics is not None:
            msg = (
                f"Cache statistics for '{device.name}': "
                f"{device.cache_statistics['cache_hits']} hits / {device.cache_statistics['total_commands_sent']} "
                f"command(s) ({device.cache_statistics['cache_hit_ratio']})"
            )
            logger.info(msg)
        else:
            logger.info("Caching is not enabled on %s", device.name)


@deprecated("This function is deprecated and will be removed in ANTA v2.0.0. Use AntaRunner class instead.", category=DeprecationWarning)
async def setup_inventory(inventory: AntaInventory, tags: set[str] | None, devices: set[str] | None, *, established_only: bool) -> AntaInventory | None:
    """Set up the inventory for the ANTA run.

    Parameters
    ----------
    inventory
        AntaInventory object that includes the device(s).
    tags
        Tags to filter devices from the inventory.
    devices
        Devices on which to run tests. None means all devices.
    established_only
        If True use return only devices where a connection is established.

    Returns
    -------
    AntaInventory | None
        The filtered inventory or None if there are no devices to run tests on.
    """
    if len(inventory) == 0:
        logger.info("The inventory is empty, exiting")
        return None

    # Filter the inventory based on the CLI provided tags and devices if any
    selected_inventory = inventory.get_inventory(tags=tags, devices=devices) if tags or devices else inventory

    with Catchtime(logger=logger, message="Connecting to devices"):
        # Connect to the devices
        await selected_inventory.connect_inventory()

    # Remove devices that are unreachable
    selected_inventory = selected_inventory.get_inventory(established_only=established_only)

    # If there are no devices in the inventory after filtering, exit
    if not selected_inventory.devices:
        msg = f"No reachable device {f'matching the tags {tags} ' if tags else ''}was found.{f' Selected devices: {devices} ' if devices is not None else ''}"
        logger.warning(msg)
        return None

    return selected_inventory


@deprecated("This function is deprecated and will be removed in ANTA v2.0.0. Use AntaRunner class instead.", category=DeprecationWarning)
def prepare_tests(
    inventory: AntaInventory, catalog: AntaCatalog, tests: set[str] | None, tags: set[str] | None
) -> defaultdict[AntaDevice, set[AntaTestDefinition]] | None:
    """Prepare the tests to run.

    Parameters
    ----------
    inventory
        AntaInventory object that includes the device(s).
    catalog
        AntaCatalog object that includes the list of tests.
    tests
        Tests to run against devices. None means all tests.
    tags
        Tags to filter devices from the inventory.

    Returns
    -------
    defaultdict[AntaDevice, set[AntaTestDefinition]] | None
        A mapping of devices to the tests to run or None if there are no tests to run.
    """
    # Build indexes for the catalog. If `tests` is set, filter the indexes based on these tests
    catalog.build_indexes(filtered_tests=tests)

    # Using a set to avoid inserting duplicate tests
    device_to_tests: defaultdict[AntaDevice, set[AntaTestDefinition]] = defaultdict(set)

    total_test_count = 0

    # Create the device to tests mapping from the tags
    for device in inventory.devices:
        if tags:
            # If there are CLI tags, execute tests with matching tags for this device
            if not (matching_tags := tags.intersection(device.tags)):
                # The device does not have any selected tag, skipping
                continue
            device_to_tests[device].update(catalog.get_tests_by_tags(matching_tags))
        else:
            # If there is no CLI tags, execute all tests that do not have any tags
            device_to_tests[device].update(catalog.tag_to_tests[None])

            # Then add the tests with matching tags from device tags
            device_to_tests[device].update(catalog.get_tests_by_tags(device.tags))

        total_test_count += len(device_to_tests[device])

    if total_test_count == 0:
        msg = (
            f"There are no tests{f' matching the tags {tags} ' if tags else ' '}to run in the current test catalog and device inventory, please verify your inputs."
        )
        logger.warning(msg)
        return None

    return device_to_tests


@deprecated("This function is deprecated and will be removed in ANTA v2.0.0. Use AntaRunner class instead.", category=DeprecationWarning)
def get_coroutines(selected_tests: defaultdict[AntaDevice, set[AntaTestDefinition]], manager: ResultManager | None = None) -> list[Coroutine[Any, Any, TestResult]]:
    """Get the coroutines for the ANTA run.

    Parameters
    ----------
    selected_tests
        A mapping of devices to the tests to run. The selected tests are generated by the `prepare_tests` function.
    manager
        An optional ResultManager object to pre-populate with the test results. Used in dry-run mode.

    Returns
    -------
    list[Coroutine[Any, Any, TestResult]]
        The list of coroutines to run.
    """
    coros = []
    for device, test_definitions in selected_tests.items():
        for test in test_definitions:
            try:
                test_instance = test.test(device=device, inputs=test.inputs)
                if manager is not None:
                    manager.add(test_instance.result)
                coros.append(test_instance.test())
            except Exception as e:  # noqa: PERF203, BLE001
                # An AntaTest instance is potentially user-defined code.
                # We need to catch everything and exit gracefully with an error message.
                message = "\n".join(
                    [
                        f"There is an error when creating test {test.test.__module__}.{test.test.__name__}.",
                        f"If this is not a custom test implementation: {GITHUB_SUGGESTION}",
                    ],
                )
                anta_log_exception(e, message, logger)
    return coros


@cprofile()
async def main(
    manager: ResultManager,
    inventory: AntaInventory,
    catalog: AntaCatalog,
    devices: set[str] | None = None,
    tests: set[str] | None = None,
    tags: set[str] | None = None,
    *,
    established_only: bool = True,
    dry_run: bool = False,
) -> None:
    """Run ANTA.

    Use this as an entrypoint to the test framework in your script.
    ResultManager object gets updated with the test results.

    Parameters
    ----------
    manager
        ResultManager object to populate with the test results.
    inventory
        AntaInventory object that includes the device(s).
    catalog
        AntaCatalog object that includes the list of tests.
    devices
        Devices on which to run tests. None means all devices. These may come from the `--device / -d` CLI option in NRFU.
    tests
        Tests to run against devices. None means all tests. These may come from the `--test / -t` CLI option in NRFU.
    tags
        Tags to filter devices from the inventory. These may come from the `--tags` CLI option in NRFU.
    established_only
        Include only established device(s).
    dry_run
        Build the list of coroutine to run and stop before test execution.
    """
    runner = AntaRunner()
    filters = AntaRunFilters(
        devices=devices,
        tests=tests,
        tags=tags,
        established_only=established_only,
    )
    await runner.run(inventory, catalog, manager, filters, dry_run=dry_run)
