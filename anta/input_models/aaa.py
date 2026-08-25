# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Input models for AAA tests."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from anta.custom_types import AAAAuthMethod

if TYPE_CHECKING:
    import sys

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


PRIVILEGE_METHOD_LIST_PATTERN = re.compile(r"^privilege(?P<start>[0-9]|1[0-5])(?:-(?P<end>[0-9]|1[0-5]))?$")
MAX_PRIVILEGE_LEVEL = 15


def _validate_method_list_names(method_lists: list[AAAMethodList], expected_names: set[str] | None = None) -> None:
    """Validate that method-list names are unique and optionally belong to a fixed set."""
    names = [method_list.name for method_list in method_lists]
    if len(names) != len(set(names)):
        msg = "AAA method-list names must be unique"
        raise ValueError(msg)

    if expected_names is not None and (invalid_names := set(names).difference(expected_names)):
        msg = f"Invalid AAA method-list name(s): {', '.join(sorted(map(str, invalid_names)))}. Expected one of: {', '.join(sorted(expected_names))}"
        raise ValueError(msg)


def _normalize_privilege_method_list_name(name: str | int) -> str:
    """Normalize and validate an EOS privilege method-list name."""
    if isinstance(name, int):
        if 0 <= name <= MAX_PRIVILEGE_LEVEL:
            return f"privilege{name}"
        msg = f"Invalid AAA privilege level: {name}. Expected an integer between 0 and 15"
        raise ValueError(msg)

    if name == "all":
        return "privilege0-15"

    if (match := PRIVILEGE_METHOD_LIST_PATTERN.fullmatch(name)) is None:
        msg = (
            f"Invalid AAA privilege method-list name: {name}. Expected an integer between 0 and 15, 'all', "
            "'privilegeN', or 'privilegeN-M', where levels are between 0 and 15"
        )
        raise ValueError(msg)

    if (end := match.group("end")) is not None and int(match.group("start")) > int(end):
        msg = f"Invalid AAA privilege method-list range: {name}. The first privilege level must not exceed the last"
        raise ValueError(msg)
    return name


class AAAMethodList(BaseModel):
    """Expected AAA authentication or authorization method list."""

    model_config = ConfigDict(extra="forbid")
    name: str | int
    """Authentication method-list name."""
    methods: list[AAAAuthMethod]
    """Authentication methods in the expected order."""


class AAAAuthentication(BaseModel):
    """AAA authentication types and their expected method lists."""

    model_config = ConfigDict(extra="forbid")
    auth_type: Literal["login", "enable", "dot1x"]
    """Authentication type using the expected method lists."""
    method_lists: list[AAAMethodList] = Field(min_length=1)
    """Expected authentication method lists."""

    @model_validator(mode="after")
    def validate_method_lists(self) -> Self:
        """Validate method-list names supported by the selected authentication type."""
        expected_names = {
            "login": {"default", "console", "command-api"},
            "enable": {"default", "console"},
            "dot1x": {"default"},
        }[self.auth_type]
        _validate_method_list_names(self.method_lists, expected_names)
        return self


class AAAAuthorization(BaseModel):
    """AAA authorization types and their expected method lists."""

    model_config = ConfigDict(extra="forbid")
    authz_type: Literal["commands", "exec"]
    """Authorization type using the expected method lists."""
    method_lists: list[AAAMethodList] = Field(min_length=1)
    """Expected authorization method lists."""

    @model_validator(mode="after")
    def validate_method_lists(self) -> Self:
        """Validate method-list names supported by the selected authorization type."""
        if self.authz_type == "commands":
            for method_list in self.method_lists:
                method_list.name = _normalize_privilege_method_list_name(method_list.name)
            _validate_method_list_names(self.method_lists)
        else:
            _validate_method_list_names(self.method_lists, {"exec"})
        return self


class AAAAccountingMethodList(BaseModel):
    """Expected AAA accounting method lists for a single EOS accounting section."""

    model_config = ConfigDict(extra="forbid")
    name: str | int
    """Accounting method-list name."""
    default_methods: list[AAAAuthMethod] | None = None
    """Expected default accounting methods in order."""
    console_methods: list[AAAAuthMethod] | None = None
    """Expected console accounting methods in order."""

    @model_validator(mode="after")
    def validate_methods(self) -> Self:
        """Require at least one accounting context to be provided."""
        if self.default_methods is None and self.console_methods is None:
            msg = "At least one of 'default_methods' or 'console_methods' must be provided"
            raise ValueError(msg)
        return self


class AAAAccounting(BaseModel):
    """AAA accounting types and their expected default or console method lists."""

    model_config = ConfigDict(extra="forbid")
    acct_type: Literal["commands", "exec", "system", "dot1x"]
    """Accounting type using the expected method lists."""
    method_lists: list[AAAAccountingMethodList] = Field(min_length=1)
    """Expected accounting method lists."""

    @model_validator(mode="after")
    def validate_method_lists(self) -> Self:
        """Validate method-list names and contexts supported by the selected accounting type."""
        if self.acct_type == "commands":
            for method_list in self.method_lists:
                method_list.name = _normalize_privilege_method_list_name(method_list.name)
            names = [method_list.name for method_list in self.method_lists]
            if len(names) != len(set(names)):
                msg = "AAA accounting method-list names must be unique"
                raise ValueError(msg)
            return self

        names = [method_list.name for method_list in self.method_lists]
        if len(names) != len(set(names)):
            msg = "AAA accounting method-list names must be unique"
            raise ValueError(msg)

        expected_name = {"exec": "exec", "system": "system", "dot1x": "dot1x"}[self.acct_type]
        if invalid_names := set(names).difference({expected_name}):
            msg = f"Invalid AAA accounting method-list name(s): {', '.join(sorted(invalid_names))}. Expected: {expected_name}"
            raise ValueError(msg)

        if self.acct_type in {"system", "dot1x"} and any(method_list.console_methods is not None for method_list in self.method_lists):
            msg = f"Console accounting methods are not supported for accounting type '{self.acct_type}'"
            raise ValueError(msg)
        return self


"""
```yaml
VerifyAAAMethods:
  authentication:
    - auth_type: login
      method_lists:
        - name: default
          methods: list[AAAAuthMethod]
        - name: console
          methods: list[AAAAuthMethod]
        - name: command-api
          methods: list[AAAAuthMethod]
    - auth_type: enable
      method_lists:
        - name: default
          methods: list[AAAAuthMethod]
        - name: console
          methods: list[AAAAuthMethod]
    - auth_type: dot1x
      method_lists:
        - name: default
          methods: list[AAAAuthMethod]
  authorization:
    - authz_type: commands
      method_lists:
        # Valid names are integers 0-15 or "all". Existing privilegeN and privilegeN-M names are also accepted.
        - name: all
          methods: list[AAAAuthMethod]
    - authz_type: exec
      method_lists:
        - name: exec
          methods: list[AAAAuthMethod]
  accounting:
    - acct_type: commands
      method_lists:
        # Valid names are integers 0-15 or "all". Existing privilegeN and privilegeN-M names are also accepted.
        - name: all
          default_methods: list[AAAAuthMethod]
          console_methods: list[AAAAuthMethod]
    - acct_type: exec
      method_lists:
        - name: exec
          default_methods: list[AAAAuthMethod]
          console_methods: list[AAAAuthMethod]
    - acct_type: system
      method_lists:
        - name: system
          default_methods: list[AAAAuthMethod]
    - acct_type: dot1x
      method_lists:
        - name: dot1x
          default_methods: list[AAAAuthMethod]
"""
