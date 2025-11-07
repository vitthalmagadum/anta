# Arista Network Test Automation (ANTA)

ANTA is a Python-based testing framework for Arista EOS devices.

## Using CloudVision Portal (CVP) as a data source

ANTA can use CVP as a data source for running tests. This allows you to run tests against the state of your devices as seen by CVP, rather than connecting to each device directly.

To use CVP as a data source, you need to provide the CVP host and credentials to the `anta nrfu` command.

### CLI Options

*   `--source cvp`: Use CVP as the data source.
*   `--cvp-host <host>`: The hostname or IP address of the CVP instance.
*   `--cvp-port <port>`: The port of the CVP instance.
*   `--cvp-user <user>`: The username to connect to CVP.
*   `--cvp-password <password>`: The password to connect to CVP.
*   `--cvp-token <token>`: The token to connect to CVP.

### Example

```bash
anta nrfu --source cvp --cvp-host 10.0.0.1 --cvp-user cvpadmin --cvp-password arista --catalog path/to/catalog.yml
```
