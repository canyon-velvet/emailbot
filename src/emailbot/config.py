"""The main config file: what it may contain, and how it's read."""

import re
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
)
from pydantic_core import ErrorDetails

# Deliberately loose: one @, no spaces, a dot in the domain. Google checks the rest.
EMAIL_ADDRESS = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class ConfigError(Exception):
    """A problem with the config file, explained in plain words for the user."""


def _email_address(value: str) -> str:
    if not EMAIL_ADDRESS.fullmatch(value):
        raise ValueError(f"{value!r} isn't a valid email address")
    return value


class SecretsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: Literal["keychain", "1password"] = "keychain"
    vault: str | None = Field(default=None, validate_default=True)

    @field_validator("vault")
    @classmethod
    def _required_for_1password(cls, vault: str | None, info: ValidationInfo):
        if info.data.get("backend") == "1password" and not vault:
            raise ValueError("required when the backend is 1password")
        return vault


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["shadow", "live"] = "shadow"
    accounts: list[Annotated[str, AfterValidator(_email_address)]] = []
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)

    @field_validator("accounts")
    @classmethod
    def _unique(cls, accounts: list[str]) -> list[str]:
        seen: set[str] = set()
        for account in accounts:
            if account.lower() in seen:
                raise ValueError(f"{account} is listed more than once")
            seen.add(account.lower())
        return accounts


def load(path: Path) -> Config:
    """Read and validate the config file, or raise `ConfigError` explaining why not."""
    try:
        # Bytes, so PyYAML detects the encoding and reports bad bytes as YAML errors.
        data = yaml.safe_load(path.read_bytes())
    except FileNotFoundError:
        message = f"No config file at {path}. Create one, or pass --config PATH."
        raise ConfigError(message) from None
    except OSError as error:
        raise ConfigError(f"Can't read {path}: {error.strerror}") from None
    except yaml.YAMLError as error:
        raise ConfigError(f"{path} isn't valid YAML{_position(error)}") from None
    try:
        return Config.model_validate({} if data is None else data)
    except ValidationError as error:
        problems = sorted(f"  {_dotted_path(e)}: {_explain(e)}" for e in error.errors())
        noun = "problem" if len(problems) == 1 else "problems"
        summary = f"{path} has {len(problems)} {noun}:"
        raise ConfigError("\n".join([summary, *problems])) from None


def _position(error: yaml.YAMLError) -> str:
    if isinstance(error, yaml.MarkedYAMLError) and (mark := error.problem_mark):
        return f" at line {mark.line + 1}, column {mark.column + 1}: {error.problem}"
    return f": {error}"


def _dotted_path(error: ErrorDetails) -> str:
    return ".".join(str(part) for part in error["loc"]) or "(whole file)"


def _explain(error: ErrorDetails) -> str:
    if error["type"] == "extra_forbidden":
        return "unknown setting"
    if error["type"] == "model_type":
        return "should be a group of `name: value` settings"
    return error["msg"].removeprefix("Value error, ")
