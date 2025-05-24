#!/usr/bin/env python3

import os
import sys
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(Exception):
    pass


@dataclass
class Config:
    # ADB Configuration (optional - for remote ADB)
    adb_host: Optional[str] = None
    adb_port: Optional[int] = None

    # InfluxDB Configuration (required)
    influxdb_url: str = None
    influxdb_token: str = None
    influxdb_org: str = None
    influxdb_bucket: str = None

    def __post_init__(self):
        # Load ADB Configuration (optional)
        self.adb_host = self._get_optional_env('ADB_HOST')
        self.adb_port = self._get_optional_int_env('ADB_PORT')

        # Load InfluxDB Configuration (required)
        self.influxdb_url = self._get_required_env('INFLUXDB_URL')
        self.influxdb_token = self._get_required_env('INFLUXDB_TOKEN')
        self.influxdb_org = self._get_required_env('INFLUXDB_ORG')
        self.influxdb_bucket = self._get_required_env('INFLUXDB_BUCKET')

    @staticmethod
    def _get_required_env(key: str) -> str:
        value = os.getenv(key)
        if not value or value.strip() == "":
            raise ConfigurationError(
                f"Required environment variable '{key}' is missing or empty. "
                f"Please set it in your .env file or environment."
            )
        return value.strip()

    @staticmethod
    def _get_optional_env(key: str) -> Optional[str]:
        value = os.getenv(key)
        if value and value.strip():
            return value.strip()
        return None

    def _get_optional_int_env(self, key: str) -> Optional[int]:
        value = self._get_optional_env(key)
        if value:
            try:
                return int(value)
            except ValueError:
                raise ConfigurationError(
                    f"Environment variable '{key}' must be a valid integer, got: '{value}'"
                )
        return None

    def get_influxdb_config(self) -> dict:
        return {
            "url": self.influxdb_url,
            "token": self.influxdb_token,
            "org": self.influxdb_org,
            "bucket": self.influxdb_bucket
        }

    def __str__(self) -> str:
        return (
            f"Config(\n"
            f"  ADB: {self.adb_host}:{self.adb_port}\n"
            f"  InfluxDB: {self.influxdb_url}\n"
            f"  Token: {self.influxdb_token}\n"
            f"  Org: {self.influxdb_org}\n"
            f"  Bucket: {self.influxdb_bucket}\n"
            f")"
        )


def load_config() -> Config:
    try:
        return Config()
    except ConfigurationError as e:
        print(f"❌ Configuration Error: {e}", file=sys.stderr)
        print("\n📝 Required environment variables:", file=sys.stderr)
        print("   - INFLUXDB_URL", file=sys.stderr)
        print("   - INFLUXDB_TOKEN", file=sys.stderr)
        print("   - INFLUXDB_ORG", file=sys.stderr)
        print("   - INFLUXDB_BUCKET", file=sys.stderr)
        print("\n📝 Optional environment variables:", file=sys.stderr)
        print("   - ADB_HOST (for remote ADB)", file=sys.stderr)
        print("   - ADB_PORT (for remote ADB)", file=sys.stderr)
        print("\n💡 Create a .env file with these variables or set them in your environment.", file=sys.stderr)
        sys.exit(1)


# Global configuration instance - will exit if config is invalid
config = load_config()
