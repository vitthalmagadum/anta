# ANTA + CloudVision Integration

## The Problem

ANTA (Arista Network Test Automation) traditionally collects device state by connecting **directly to each device** over eAPI (HTTP/HTTPS). This works well in lab environments but creates challenges in production:

- Requires direct IP reachability to every device
- Requires per-device credentials
- Each test run adds live load to devices via eAPI polling

## The Idea

> **What if ANTA could read device state from CloudVision instead of polling devices directly?**

CloudVision already has a continuously updated, streaming copy of every device's state — interfaces, LLDP neighbors, software version, and more — stored in its internal telemetry database. This branch adds a **CVP data path** to ANTA, allowing the same ANTA tests to run against data already present in CloudVision via gRPC, with zero additional load on the devices.

---

## Architecture

### Before: Direct eAPI

```
┌─────────────────────────────────────┐
│              ANTA                   │
│                                     │
│  AntaInventory                      │
│    └── AsyncEOSDevice (per host)    │
│          └── _collect()             │
│               │  HTTP/eAPI          │
└───────────────┼─────────────────────┘
                │
    ┌───────────▼──────────┐
    │   Device (EOS)       │   ← direct connection, adds load
    └──────────────────────┘
```

### After: CVP gRPC Path

```
┌──────────────────────────────────────────────┐
│                   ANTA                       │
│                                              │
│  AntaInventory                               │
│    └── CVPDevice (per host)  ← NEW           │
│          └── _collect()                      │
│               │  dispatches via mapping      │
│               ▼                              │
│          CvpClient  ← NEW                    │
│               │  gRPC (port 443)             │
└───────────────┼──────────────────────────────┘
                │
    ┌───────────▼──────────────────────────┐
    │         CloudVision (CVP)            │
    │                                      │
    │  Streaming telemetry database        │
    │  (Sysdb paths, analytics dataset)    │
    │                                      │
    │  Devices stream state continuously ──┼──► EOS Device 1
    │  No extra polling needed             │    EOS Device 2
    └──────────────────────────────────────┘    EOS Device N
```

---

## How It Works — Data Flow

```
anta nrfu --test-source cvp --cvp-host cvp.example.com \
          --token-file /path/to/token --crt-file /path/to/ca.crt \
          --inventory inventory.yaml --catalog catalog.yaml

         │
         ▼
  CLI parses --test-source cvp  (anta/cli/utils.py)
         │
         ▼
  AntaInventory.parse_inventory_file()
    └── for each host → creates CVPDevice (instead of AsyncEOSDevice)
         │
         ▼
  Test runner calls CVPDevice._collect(command)
    └── looks up command in cvp_eapi_mapping:
          "show version"              → get_device_version()
          "show interfaces description" → get_interface_status()
          "show lldp neighbors detail"  → get_lldp_neighbors()
         │
         ▼
  CvpClient queries CVP Sysdb/analytics over gRPC
    └── returns data in eAPI-compatible format
         │
         ▼
  ANTA test logic runs unchanged — same tests, same results
```

---

### New File: `anta/cvp_device.py` — `CVPDevice`

A new `AntaDevice` subclass that slots into ANTA's existing test framework:

```python
class CVPDevice(AntaDevice):
    def __init__(self, cvp_host, token_file, crt_file, name, test_source):
        self.cvp_client = CvpClient(host=cvp_host, token_file=token_file, ca_file=crt_file)
        super().__init__(name=name, test_source=test_source)

    async def _collect(self, command, ...):
        method_name = self.cvp_client.cvp_eapi_mapping.get(command.command)
        method = getattr(self.cvp_client, method_name)
        command.output = method(hostname=self.name)
```

Because `CVPDevice` extends `AntaDevice` and populates `command.output` in the same format as eAPI, **all existing ANTA tests work without modification**.

---

## What Was Built

### New Package: `cvp/`

| File | Purpose |
|---|---|
| [`cvp/__init__.py`](cvp/__init__.py) | Package entry point, exports `CvpClient` |
| [`cvp/cvp_connection.py`](cvp/cvp_connection.py) | Core gRPC client — connects to CVP, runs queries |
| [`cvp/cvp_eapi_mapping.py`](cvp/cvp_eapi_mapping.py) | Maps eAPI command strings to `CvpClient` methods |
| [`cvp/utils.py`](cvp/utils.py) | Low-level Sysdb helpers for interface and device queries |

#### `CvpClient` — Key Methods

| Method | CVP Data Source | Returns |
|---|---|---|
| `get_device_version(hostname)` | `analytics` dataset → `Eos/image` | `{"version": "4.29.x"}` |
| `get_interface_status(hostname)` | `Sysdb/interface/status/eth/phy` | eAPI-compatible interface dict |
| `get_lldp_neighbors(hostname)` | `Sysdb/l2discovery/lldp/status` | eAPI-compatible LLDP neighbor dict |

#### Interface Status — Chassis vs. Fixed Device Handling

A key complexity: modular (chassis) devices store interface state per linecard, while fixed devices store it under a single slice. The `cvp/utils.py` module handles both automatically:

```
device_type()  ─── checks Sysdb/hardware/entmib
    │
    ├── "modular"  → get_intf_status_chassis()  (iterates over linecards)
    └── "fixed"    → get_intf_status_fixed()    (reads slice/1 directly)
```

## Modified Files

### `anta/device.py`
Added `test_source` attribute (`"eapi"` | `"cvp"`) to `AntaDevice` base class so every device knows which data path it uses.

### `anta/inventory/__init__.py`

| Behaviour | eAPI (default) | CVP |
|---|---|---|
| Device class | `AsyncEOSDevice` | `CVPDevice` |
| Connectivity check | `refresh()` called | skipped (no TCP handshake needed) |
| Host filtering | By tags/name | Always included |
| Supported inventory types | hosts, networks, ranges | hosts only |

### `anta/cli/utils.py`

Four new CLI flags added to all ANTA subcommands:

```
--test-source [eapi|cvp]   Source for test data (default: eapi)
--cvp-host TEXT            CloudVision hostname or IP
--token-file / -T PATH     Path to CVP API token file
--crt-file PATH            Path to CA certificate for TLS
```

---

## eAPI Command → CVP Mapping

The `cvp_eapi_mapping` dict is the bridge between ANTA's command-based tests and CVP's path-based telemetry. Currently supported:

| ANTA Test | eAPI Command | CVP Method | CVP Data Path |
|---|---|---|---|
| `VerifyEOSVersion` | `show version` | `get_device_version` | `analytics/Eos/image` |
| `VerifyInterfacesStatus` | `show interfaces description` | `get_interface_status` | `Sysdb/interface/status/eth/phy/...` |
| `VerifyLLDPNeighbors` | `show lldp neighbors detail` | `get_lldp_neighbors` | `Sysdb/l2discovery/lldp/status/...` |

---

## Example Usage

```bash
# Run ANTA tests using CVP as the data source
anta nrfu \
  --test-source cvp \
  --cvp-host cvp.example.com \
  --token-file ~/.cvp/token \
  --crt-file ~/.cvp/cvp.crt \
  --inventory inventory.yaml \
  --catalog catalog.yaml \
  --log-level INFO
```

No changes to the inventory file or catalog — only the data source changes.

---
