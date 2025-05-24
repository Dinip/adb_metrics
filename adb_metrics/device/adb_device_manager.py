#!/usr/bin/env python3

import logging
from typing import List, Dict, Optional

from adb_metrics.config.adb_config import adb_config
from adb_metrics.device.android_metrics_collector import AndroidMetricsCollector

logger = logging.getLogger(__name__)


class ADBDeviceManager:
    @staticmethod
    def get_connected_devices() -> List[str]:
        try:
            result = adb_config.run_adb_command("devices", timeout=10)
            if not result:
                return []

            devices = []
            lines = result.strip().split('\n')[1:]  # Skip header

            for line in lines:
                if '\tdevice' in line:
                    device_serial = line.split('\t')[0]
                    devices.append(device_serial)

            return devices
        except Exception as e:
            logger.error(f"Error getting connected devices: {e}")
            return []

    @staticmethod
    def get_device_info(device_serial: str) -> Dict[str, str]:
        info = {"serial": device_serial}

        model_output = adb_config.run_adb_command("shell getprop ro.product.model", device_serial)
        if model_output:
            info["model"] = model_output.strip()

        version_output = adb_config.run_adb_command("shell getprop ro.build.version.release", device_serial)
        if version_output:
            info["android_version"] = version_output.strip()

        manufacturer_output = adb_config.run_adb_command("shell getprop ro.product.manufacturer", device_serial)
        if manufacturer_output:
            info["manufacturer"] = manufacturer_output.strip()

        return info

    @staticmethod
    def collect_from_all_devices(app_patterns: Optional[List[str]]):
        devices = ADBDeviceManager.get_connected_devices()

        if not devices:
            logger.warning("No devices connected")
            return []

        all_metrics = []
        for device_serial in devices:
            logger.info(f"Collecting from device: {device_serial}")
            device_info = ADBDeviceManager.get_device_info(device_serial)
            logger.info(f"Device info: {device_info}")

            collector = AndroidMetricsCollector(device_serial)
            metrics = collector.collect_all_metrics(app_patterns)
            all_metrics.extend(metrics)

        return all_metrics
