#!/usr/bin/env python3

import argparse
import logging
import sys
import time
from typing import Optional, List

from adb_metrics.config.adb_config import adb_config
from adb_metrics.config.config import config
from adb_metrics.data.influxdb import InfluxDBPersistence, ConsolePrinter
from adb_metrics.device.adb_device_manager import ADBDeviceManager
from adb_metrics.device.android_metrics_collector import AndroidMetricsCollector, MetricPoint

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def collect_metrics(device_id: Optional[str], app_patterns: Optional[List[str]]) -> List[MetricPoint]:
    if device_id:
        collector = AndroidMetricsCollector(device_id)
        metrics = collector.collect_all_metrics(app_patterns)
    else:
        metrics = ADBDeviceManager.collect_from_all_devices(app_patterns)

    return metrics


def collect_and_print(device_id: Optional[str], app_patterns: Optional[List[str]]):
    ConsolePrinter.print_metrics(collect_metrics(device_id, app_patterns))


def collect_and_persist(device_id: Optional[str], app_patterns: Optional[List[str]], interval: int):
    try:
        persistence = InfluxDBPersistence()
    except Exception as e:
        logger.error(f"Failed to initialize InfluxDB connection: {e}")
        sys.exit(1)

    try:
        logger.info(f"Starting continuous collection every {interval} seconds...")
        logger.info(f"Configuration: {config}")

        while True:
            metrics = collect_metrics(device_id, app_patterns)

            if metrics:
                success = persistence.write_metrics(metrics)
                if success:
                    logger.info(f"Collected and persisted {len(metrics)} metrics")
                else:
                    logger.error("Failed to persist metrics")
            else:
                logger.warning("No metrics collected")

            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("Stopping collection...")
    finally:
        persistence.close()


def list_devices():
    devices = ADBDeviceManager.get_connected_devices()

    if not devices:
        print("No devices connected")
        return

    print("Connected devices:")
    for device_serial in devices:
        device_info = ADBDeviceManager.get_device_info(device_serial)
        print(f"  {device_serial}: {device_info.get('manufacturer', 'Unknown')} "
              f"{device_info.get('model', 'Unknown')} "
              f"(Android {device_info.get('android_version', 'Unknown')})")


def test_adb_connection() -> bool:
    print("=== ADB Functionality Test ===")
    try:
        version = ADBDeviceManager.get_version()
        print(f"ADB Version: {version}")
        print("\n✅ ADB is functioning correctly")
        return True
    except Exception as e:
        print("\n❌ ADB test failed:")
        print(f"Error: {e}")
        return False


def show_config():
    print("✅ Current Configuration:")
    print(config)


def main():
    parser = argparse.ArgumentParser(description="Android Metrics Collector")
    parser.add_argument(
        "mode",
        choices=["print", "persist", "devices", "config"],
        help="Operation mode: print to console, persist to InfluxDB, list devices, or show config"
    )
    parser.add_argument(
        "--device-id",
        help="Specific device ID/serial (if not provided, collects from all devices)"
    )
    parser.add_argument(
        "--app-pattern",
        action="append",
        help="App package pattern(s) to monitor (e.g., '*.bmw.*'). Can be specified multiple times. If not provided, only global metrics will be collected."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Collection interval in seconds for persist mode (default: 30)"
    )
    parser.add_argument(
        "--adb-host",
        help="ADB server host (overrides .env/environment)"
    )
    parser.add_argument(
        "--adb-port",
        type=int,
        help="ADB server port (overrides .env/environment)"
    )
    parser.add_argument(
        "--adb-test",
        action="store_true",
        help="Test ADB functionality by printing version and device information"
    )

    args = parser.parse_args()

    # Update ADB configuration with CLI overrides
    if args.adb_host or args.adb_port:
        adb_config.update_config(host=args.adb_host, port=args.adb_port)

    # If --adb-test flag is used, run the test and exit
    if args.adb_test:
        test_success = test_adb_connection()
        sys.exit(0 if test_success else 1)

    if args.mode == "config":
        show_config()
    elif args.mode == "devices":
        list_devices()
    elif args.mode == "print":
        collect_and_print(args.device_id, args.app_pattern)
    elif args.mode == "persist":
        collect_and_persist(args.device_id, args.app_pattern, args.interval)


if __name__ == "__main__":
    main()
