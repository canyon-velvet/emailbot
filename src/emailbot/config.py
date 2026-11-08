"""The main config file: what it may contain, and how it's read."""

import ipaddress
import re
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

import yaml
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_core import ErrorDetails
from yaml.composer import ComposerError
from yaml.reader import ReaderError

# Plain ASCII addresses only: dot-separated words, then dot-separated domain labels
# ending in a top-level domain of letters. Google checks the rest.
_EMAIL_ADDRESS = re.compile(
    r"[A-Za-z0-9_%+'-]+(?:\.[A-Za-z0-9_%+'-]+)*"
    r"@(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}"
)

# Where a model marked `local: true` may be: this computer or a private network.
# Link-local addresses are left out: cloud metadata services use them.
_LOCAL_NETWORKS = [
    ipaddress.ip_network(network)
    for network in (
        "127.0.0.0/8",  # loopback
        "::1/128",
        "10.0.0.0/8",  # private (RFC 1918)
        "172.16.0.0/12",
        "192.168.0.0/16",
        "fc00::/7",  # IPv6 unique-local
    )
]
_LOCAL_NAME_SUFFIXES = (".local", ".home.arpa")


class ConfigError(Exception):
    """A problem with the config file, explained in plain words for the user."""


class _StrictLoader(yaml.SafeLoader):
    """PyYAML's safe loader, but a setting given twice is an error, not "last wins"."""

    # Checked as each mapping is read, before `<<` merges copy keys into it.
    def compose_mapping_node(self, anchor) -> yaml.MappingNode:
        node = super().compose_mapping_node(anchor)
        seen: set[tuple[str, str]] = set()
        for key_node, _ in node.value:
            if isinstance(key_node, yaml.ScalarNode):
                key = (key_node.tag, key_node.value)
                if key in seen:
                    problem = f"{key_node.value!r} is set more than once"
                    raise ComposerError(None, None, problem, key_node.start_mark)
                seen.add(key)
        return node


def _host(url: str) -> str | None:
    """The lowercased host of an http(s) address, or None if it isn't one."""
    try:
        address = urlsplit(url)
    except ValueError:  # e.g. an unclosed IPv6 bracket
        return None
    return address.hostname if address.scheme in ("http", "https") else None


def _not_local(host: str) -> str | None:
    """Why a model at `host` can't be marked local, or None if it can."""
    if host == "localhost" or host.endswith(_LOCAL_NAME_SUFFIXES):
        return None
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:  # a name, other than the ones above
        ip = None
    if ip and ip.is_link_local:
        return (
            "is a link-local address, which cloud metadata services use, so it "
            "can't count as local"
        )
    if ip and any(ip in network for network in _LOCAL_NETWORKS):
        return None
    return (
        "isn't on this computer or a private network (local allows localhost, "
        "loopback and private IP addresses, and names ending in .local or .home.arpa)"
    )


def _email_address(value: str) -> str:
    if not _EMAIL_ADDRESS.fullmatch(value):
        raise ValueError(f"{value!r} isn't a valid email address")
    return value


class _Section(BaseModel):
    """A group of settings. Unknown names are errors; an empty value means default."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _empty_means_default(cls, data: object) -> object:
        if isinstance(data, dict):
            return {
                name: value
                for name, value in data.items()
                if value is not None or name not in cls.model_fields
            }
        return data


class SecretsConfig(_Section):
    backend: Literal["keychain", "1password"] = "keychain"
    vault: str | None = Field(default=None, validate_default=True)

    @field_validator("vault")
    @classmethod
    def _for_1password_only(cls, vault: str | None, info: ValidationInfo) -> str | None:
        backend = info.data.get("backend")
        if backend == "1password" and not (vault or "").strip():
            raise ValueError("required when the backend is 1password")
        if backend == "keychain" and vault is not None:
            raise ValueError("only used when the backend is 1password")
        return vault


class ModelConfig(_Section):
    """The model for one task."""

    provider: Literal["openai", "anthropic", "gemini", "openai-compatible"]
    model: str
    base_url: str | None = Field(default=None, validate_default=True)
    local: bool = False

    @field_validator("base_url")
    @classmethod
    def _full_address(cls, base_url: str | None, info: ValidationInfo) -> str | None:
        if base_url is None:
            if info.data.get("provider") == "openai-compatible":
                raise ValueError("required when the provider is openai-compatible")
            return None
        if _host(base_url) is None:
            raise ValueError(
                "should be a full address such as http://localhost:11434/v1"
            )
        return base_url

    @field_validator("local")
    @classmethod
    def _on_this_computer_or_network(cls, local: bool, info: ValidationInfo) -> bool:
        # Skipped if provider or base_url already failed: that error is reported.
        if not local or "provider" not in info.data or "base_url" not in info.data:
            return local
        if info.data["provider"] != "openai-compatible":
            raise ValueError(
                "only for the openai-compatible provider: openai, anthropic and "
                "gemini are cloud services"
            )
        host = _host(info.data["base_url"]) or ""
        if problem := _not_local(host):
            raise ValueError(f"{host!r} {problem}")
        return local


class ModelsConfig(_Section):
    classify: ModelConfig | None = None
    digest: ModelConfig | None = None
    draft: ModelConfig | None = None


class Config(_Section):
    mode: Literal["shadow", "live"] = "shadow"
    accounts: list[Annotated[str, AfterValidator(_email_address)]] = []
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)

    @field_validator("accounts")
    @classmethod
    def _unique(cls, accounts: list[str]) -> list[str]:
        seen: set[str] = set()
        for account in accounts:
            if account.lower() in seen:
                raise ValueError(f"{account!r} is listed more than once")
            seen.add(account.lower())
        return accounts


def load(path: Path) -> Config:
    """Read and validate the config file, or raise `ConfigError` explaining why not."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        message = f"No config file at {path}. Create one, or pass --config PATH."
        raise ConfigError(message) from None
    except OSError as error:
        raise ConfigError(f"Can't read {path}: {error.strerror or error}") from None
    try:
        # Bytes, so PyYAML detects the encoding and reports bad bytes as YAML errors.
        # S506: _StrictLoader is a SafeLoader, so it can't run Python tags either.
        data = yaml.load(raw, Loader=_StrictLoader)  # noqa: S506
    except yaml.YAMLError as error:
        raise ConfigError(f"{path} isn't valid YAML{_yaml_problem(error)}") from None
    except (ValueError, KeyError, AttributeError):
        # PyYAML raises these, not YAMLError, for e.g. `!!int abc` or `!!bool maybe`.
        message = f"{path} isn't valid YAML: a value doesn't match its `!!` type tag"
        raise ConfigError(message) from None
    except RecursionError:
        raise ConfigError(f"{path} is nested too deeply to read") from None
    try:
        return Config.model_validate({} if data is None else data)
    except ValidationError as error:
        problems = [f"  {_dotted_path(e)}: {_explain(e)}" for e in error.errors()]
        noun = "problem" if len(problems) == 1 else "problems"
        summary = f"{path} has {len(problems)} {noun}:"
        raise ConfigError("\n".join([summary, *problems])) from None


def _yaml_problem(error: yaml.YAMLError) -> str:
    if isinstance(error, ReaderError):
        position = error.position + 1
        return f": unreadable or disallowed character at position {position}"
    if isinstance(error, yaml.MarkedYAMLError) and (mark := error.problem_mark):
        problem = ", ".join(part for part in (error.context, error.problem) if part)
        return f" at line {mark.line + 1}, column {mark.column + 1}: {problem}"
    return f": {error}"


def _dotted_path(error: ErrorDetails) -> str:
    # repr() quotes an empty setting name, and shows control characters as escapes
    # so a crafted name can't send commands to the user's terminal.
    parts = [
        repr(part)
        if isinstance(part, str) and not (part and part.isprintable())
        else str(part)
        for part in error["loc"]
    ]
    return ".".join(parts) or "(whole file)"


def _explain(error: ErrorDetails) -> str:
    if error["type"] == "extra_forbidden":
        return "unknown setting"
    if error["type"] == "model_type":
        return "should be a group of `name: value` settings"
    return error["msg"].removeprefix("Value error, ")
