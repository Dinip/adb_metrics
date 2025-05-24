#!/usr/bin/env python3

import subprocess
from typing import List, Optional

from adb_metrics.config.config import config


class ADBConfig:
    def __init__(self):
        self.host = config.adb_host
        self.port = config.adb_port

    def update_config(self, host: str = None, port: int = None):
        if host is not None:
            self.host = host
        if port is not None:
            self.port = port

    def build_adb_command(self, device_serial: str = None) -> List[str]:
        # ADB should be available in PATH
        cmd = ['adb']

        if self.host:
            cmd.extend(['-H', self.host])

        if self.port:
            cmd.extend(['-P', str(self.port)])

        if device_serial and device_serial != "unknown":
            cmd.extend(['-s', device_serial])

        return cmd

    def run_adb_command(self, command: str, device_serial: str = None, timeout: int = 30) -> Optional[str]:
        try:
            base_cmd = self.build_adb_command(device_serial)
            result = subprocess.run(base_cmd + command.split(), capture_output=True, text=True, timeout=timeout)
            return result.stdout if result.returncode == 0 else None
        except Exception as e:
            from logging import getLogger
            logger = getLogger(__name__)
            logger.error(f"Error running ADB command '{command}': {e}")
            return None


# Global ADB configuration instance
adb_config = ADBConfig()
