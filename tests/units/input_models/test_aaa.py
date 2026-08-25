# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Tests for anta.input_models.aaa."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from anta.input_models.aaa import AAAAccounting, AAAAuthentication, AAAAuthorization


@pytest.mark.parametrize(
    ("model", "data"),
    [
        pytest.param(
            AAAAuthentication,
            {
                "auth_type": "login",
                "method_lists": [
                    {"name": "default", "methods": ["tacacs+", "local"]},
                    {"name": "console", "methods": ["local"]},
                    {"name": "command-api", "methods": ["local"]},
                ],
            },
            id="authentication-login",
        ),
        pytest.param(
            AAAAuthentication,
            {"auth_type": "enable", "method_lists": [{"name": "default", "methods": ["local"]}, {"name": "console", "methods": ["local"]}]},
            id="authentication-enable",
        ),
        pytest.param(
            AAAAuthentication,
            {"auth_type": "dot1x", "method_lists": [{"name": "default", "methods": ["radius"]}]},
            id="authentication-dot1x",
        ),
        pytest.param(
            AAAAuthorization,
            {
                "authz_type": "commands",
                "method_lists": [{"name": "privilege0", "methods": ["local"]}, {"name": "privilege10-15", "methods": ["tacacs+", "local"]}],
            },
            id="authorization-commands",
        ),
        pytest.param(
            AAAAuthorization,
            {"authz_type": "exec", "method_lists": [{"name": "exec", "methods": ["tacacs+", "local"]}]},
            id="authorization-exec",
        ),
        pytest.param(
            AAAAccounting,
            {
                "acct_type": "commands",
                "method_lists": [
                    {"name": "privilege0-15", "default_methods": ["tacacs+"], "console_methods": ["tacacs+"]},
                    {"name": "privilege5", "default_methods": ["logging"]},
                ],
            },
            id="accounting-commands",
        ),
        pytest.param(
            AAAAccounting,
            {"acct_type": "exec", "method_lists": [{"name": "exec", "default_methods": ["tacacs+"], "console_methods": ["logging"]}]},
            id="accounting-exec",
        ),
        pytest.param(
            AAAAccounting,
            {"acct_type": "system", "method_lists": [{"name": "system", "default_methods": ["tacacs+"]}]},
            id="accounting-system",
        ),
        pytest.param(
            AAAAccounting,
            {"acct_type": "dot1x", "method_lists": [{"name": "dot1x", "default_methods": ["radius"]}]},
            id="accounting-dot1x",
        ),
    ],
)
def test_valid_models(model: type[AAAAuthentication | AAAAuthorization | AAAAccounting], data: dict[str, object]) -> None:
    """Valid AAA method-list combinations are accepted."""
    model.model_validate(data)


@pytest.mark.parametrize("model", [AAAAuthorization, AAAAccounting])
@pytest.mark.parametrize(
    ("name", "expected_name"),
    [pytest.param(0, "privilege0", id="zero"), pytest.param(15, "privilege15", id="fifteen"), pytest.param("all", "privilege0-15", id="all")],
)
def test_command_privilege_name_normalization(
    model: type[AAAAuthorization | AAAAccounting], name: str | int, expected_name: str
) -> None:
    """Command privilege aliases are normalized to EOS method-list names."""
    type_key = "authz_type" if model is AAAAuthorization else "acct_type"
    methods = {"methods": ["local"]} if model is AAAAuthorization else {"default_methods": ["logging"]}

    result = model.model_validate({type_key: "commands", "method_lists": [{"name": name, **methods}]})

    assert result.method_lists[0].name == expected_name


@pytest.mark.parametrize(
    ("model", "data"),
    [
        pytest.param(
            AAAAuthentication,
            {"auth_type": "dot1x", "method_lists": [{"name": "console", "methods": ["radius"]}]},
            id="authentication-invalid-name",
        ),
        pytest.param(
            AAAAuthentication,
            {"auth_type": "login", "method_lists": [{"name": "default", "methods": ["local"]}, {"name": "default", "methods": ["local"]}]},
            id="authentication-duplicate-name",
        ),
        pytest.param(
            AAAAuthorization,
            {"authz_type": "commands", "method_lists": [{"name": "privilege16", "methods": ["local"]}]},
            id="authorization-out-of-range",
        ),
        pytest.param(
            AAAAuthorization,
            {"authz_type": "commands", "method_lists": [{"name": -1, "methods": ["local"]}]},
            id="authorization-negative-level",
        ),
        pytest.param(
            AAAAccounting,
            {"acct_type": "commands", "method_lists": [{"name": 16, "default_methods": ["logging"]}]},
            id="accounting-numeric-level-out-of-range",
        ),
        pytest.param(
            AAAAuthorization,
            {"authz_type": "commands", "method_lists": [{"name": "privilege15-10", "methods": ["local"]}]},
            id="authorization-reversed-range",
        ),
        pytest.param(
            AAAAuthorization,
            {"authz_type": "exec", "method_lists": [{"name": "default", "methods": ["local"]}]},
            id="authorization-invalid-exec-name",
        ),
        pytest.param(
            AAAAccounting,
            {"acct_type": "exec", "method_lists": [{"name": "exec"}]},
            id="accounting-missing-methods",
        ),
        pytest.param(
            AAAAccounting,
            {"acct_type": "system", "method_lists": [{"name": "system", "console_methods": ["tacacs+"]}]},
            id="accounting-unsupported-console",
        ),
        pytest.param(
            AAAAccounting,
            {"acct_type": "dot1x", "method_lists": [{"name": "system", "default_methods": ["radius"]}]},
            id="accounting-invalid-name",
        ),
        pytest.param(
            AAAAccounting,
            {
                "acct_type": "commands",
                "method_lists": [
                    {"name": "privilege5", "default_methods": ["logging"]},
                    {"name": "privilege5", "console_methods": ["logging"]},
                ],
            },
            id="accounting-duplicate-name",
        ),
        pytest.param(
            AAAAccounting,
            {
                "acct_type": "commands",
                "method_lists": [
                    {"name": "all", "default_methods": ["logging"]},
                    {"name": "privilege0-15", "console_methods": ["logging"]},
                ],
            },
            id="accounting-duplicate-normalized-name",
        ),
    ],
)
def test_invalid_models(model: type[AAAAuthentication | AAAAuthorization | AAAAccounting], data: dict[str, object]) -> None:
    """Invalid AAA method-list combinations are rejected."""
    with pytest.raises(ValidationError):
        model.model_validate(data)
