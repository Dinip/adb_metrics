#!/usr/bin/env python3

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Optional

from adb_metrics.config.adb_config import adb_config

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    measurement: str
    tags: Dict[str, str]
    fields: Dict[str, float]
    timestamp: datetime


class AndroidMetricsCollector:
    def __init__(self, device_id: str = None):
        self.device_id = device_id
        self.device_serial = self._get_device_serial()

    def _get_device_serial(self) -> str:
        if self.device_id:
            return self.device_id

        try:
            result = adb_config.run_adb_command("devices", timeout=10)
            if result:
                lines = result.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    if '\tdevice' in line:
                        return line.split('\t')[0]
        except Exception as e:
            logger.error(f"Error getting device serial: {e}")

        return "unknown"

    def run_adb_command(self, command: str) -> Optional[str]:
        return adb_config.run_adb_command(f"shell {command}", self.device_serial)

    def get_installed_packages(self, pattern: str = None) -> List[str]:
        output = self.run_adb_command("pm list packages")
        if not output:
            return []

        packages = []
        for line in output.strip().split('\n'):
            if line.startswith('package:'):
                package_name = line.replace('package:', '')
                if pattern:
                    if re.search(pattern.replace('*', '.*'), package_name):
                        packages.append(package_name)
                else:
                    packages.append(package_name)

        return packages

    def collect_temperature_metrics(self) -> List[MetricPoint]:
        points = []
        current_time = datetime.now(timezone.utc)
        base_tags = {"device_serial": self.device_serial}

        # Battery temperature
        battery_output = self.run_adb_command("dumpsys battery")
        if battery_output:
            temp_match = re.search(r"temperature: (\d+)", battery_output)
            if temp_match:
                battery_temp = int(temp_match.group(1)) / 10.0
                points.append(
                    MetricPoint(
                        measurement="temperature",
                        tags={**base_tags, "sensor": "battery"},
                        fields={"value": battery_temp},
                        timestamp=current_time,
                    )
                )

        # Thermal zones
        thermal_output = self.run_adb_command("dumpsys thermal")
        if thermal_output:
            thermal_lines = thermal_output.split("\n")
            for line in thermal_lines:
                if "Temperature" in line and "mValue=" in line:
                    match = re.search(r"mType=(\w+).*mValue=([\d.]+)", line)
                    if match:
                        sensor_type = match.group(1)
                        temp_value = float(match.group(2))
                        points.append(
                            MetricPoint(
                                measurement="temperature",
                                tags={**base_tags, "sensor": sensor_type},
                                fields={"value": temp_value},
                                timestamp=current_time,
                            )
                        )

        return points

    def _parse_proc_stat(self) -> Optional[Dict[str, float]]:
        """Parse /proc/stat for CPU metrics"""
        try:
            stat_output = self.run_adb_command("cat /proc/stat")
            if not stat_output:
                return None

            # Parse first line which contains overall CPU stats
            first_line = stat_output.split('\n')[0]
            if not first_line.startswith('cpu '):
                return None

            # Format: cpu user nice system idle iowait irq softirq steal guest guest_nice
            parts = first_line.split()[1:]  # Skip 'cpu' label
            if len(parts) < 4:
                return None

            user = int(parts[0])
            nice = int(parts[1])
            system = int(parts[2])
            idle = int(parts[3])
            iowait = int(parts[4]) if len(parts) > 4 else 0
            irq = int(parts[5]) if len(parts) > 5 else 0
            softirq = int(parts[6]) if len(parts) > 6 else 0

            total = user + nice + system + idle + iowait + irq + softirq

            if total == 0:
                return None

            return {
                "user_percent": (user / total) * 100,
                "nice_percent": (nice / total) * 100,
                "system_percent": (system / total) * 100,
                "idle_percent": (idle / total) * 100,
                "iowait_percent": (iowait / total) * 100,
                "total_usage_percent": ((total - idle) / total) * 100
            }
        except Exception as e:
            logger.error(f"Error parsing /proc/stat: {e}")
            return None

    def _parse_top_cpu(self) -> Optional[Dict[str, float]]:
        """Parse top command for CPU metrics (fallback method)"""
        try:
            top_output = self.run_adb_command("top -n 1 -d 1")
            if not top_output:
                return None

            logger.debug("Top output sample:")
            lines = top_output.split('\n')[:10]
            for i, line in enumerate(lines):
                logger.debug(f"Line {i}: {line}")

            # Look for CPU line in various formats
            cpu_patterns = [
                r"CPU:\s*(\d+(?:\.\d+)?)%\s*usr.*?(\d+(?:\.\d+)?)%\s*sys.*?(\d+(?:\.\d+)?)%\s*idle",
                r"(\d+(?:\.\d+)?)%\s*cpu.*?(\d+(?:\.\d+)?)%\s*user.*?(\d+(?:\.\d+)?)%\s*sys",
                r"Tasks:.*?(\d+(?:\.\d+)?)%\s*user.*?(\d+(?:\.\d+)?)%\s*system.*?(\d+(?:\.\d+)?)%\s*idle"
            ]

            for line in lines:
                if "cpu" in line.lower() or "%" in line:
                    for pattern in cpu_patterns:
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            groups = match.groups()
                            if len(groups) >= 3:
                                user_cpu = float(groups[0])
                                system_cpu = float(groups[1])
                                idle_cpu = float(groups[2])
                                total_usage = 100 - idle_cpu

                                return {
                                    "user_percent": user_cpu,
                                    "system_percent": system_cpu,
                                    "idle_percent": idle_cpu,
                                    "total_usage_percent": total_usage
                                }

            logger.warning("Could not parse CPU info from top command")
            return None

        except Exception as e:
            logger.error(f"Error parsing top output: {e}")
            return None

    def collect_global_system_metrics(self) -> List[MetricPoint]:
        """Collect global CPU and memory metrics"""
        points = []
        current_time = datetime.now(timezone.utc)
        base_tags = {"device_serial": self.device_serial}

        # Memory info
        meminfo_output = self.run_adb_command("cat /proc/meminfo")
        if meminfo_output:
            mem_data = {}
            for line in meminfo_output.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    value_kb = (
                        int(re.findall(r"\d+", value)[0])
                        if re.findall(r"\d+", value)
                        else 0
                    )
                    mem_data[key.strip()] = value_kb * 1024

            if "MemTotal" in mem_data and "MemAvailable" in mem_data:
                total_memory = mem_data["MemTotal"]
                available_memory = mem_data["MemAvailable"]
                used_memory = total_memory - available_memory
                memory_usage_percent = (used_memory / total_memory) * 100

                points.append(
                    MetricPoint(
                        measurement="system_memory",
                        tags=base_tags,
                        fields={
                            "total_bytes": total_memory,
                            "used_bytes": used_memory,
                            "available_bytes": available_memory,
                            "usage_percent": memory_usage_percent,
                        },
                        timestamp=current_time,
                    )
                )

        # CPU usage - try /proc/stat first, then top as fallback
        cpu_data = self._parse_proc_stat()
        if not cpu_data:
            logger.info("Failed to parse /proc/stat, trying top command...")
            cpu_data = self._parse_top_cpu()

        if cpu_data:
            points.append(
                MetricPoint(
                    measurement="system_cpu",
                    tags=base_tags,
                    fields=cpu_data,
                    timestamp=current_time,
                )
            )
        else:
            logger.warning("Could not collect CPU metrics from any method")

        return points

    def _get_app_cpu_from_dumpsys(self, package_name: str) -> Optional[float]:
        try:
            cpuinfo_output = self.run_adb_command("dumpsys cpuinfo")
            if not cpuinfo_output:
                return None

            lines = cpuinfo_output.split('\n')
            for line in lines:
                if package_name in line and '%' in line:
                    # Extract percentage from line like: "12.3% 1234/com.microsoft.office.outlook: 8.9% user + 3.4% kernel"
                    match = re.search(r'(\d+(?:\.\d+)?)%', line)
                    if match:
                        return float(match.group(1))

            return None
        except Exception as e:
            logger.error(f"Error getting CPU from dumpsys for {package_name}: {e}")
            return None

    def _get_app_cpu_from_top(self, package_name: str) -> Optional[float]:
        try:
            top_output = self.run_adb_command(f"top -n 1 | grep {package_name}")
            if not top_output:
                return None

            lines = top_output.strip().split('\n')
            total_cpu = 0
            for line in lines:
                if package_name in line:
                    # Try different column positions for CPU%
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if '%' in part:
                            try:
                                cpu_percent = float(part.replace('%', ''))
                                total_cpu += cpu_percent
                                break
                            except ValueError:
                                continue

                    # Fallback: try common positions (usually column 8 or 9)
                    if total_cpu == 0 and len(parts) >= 9:
                        for pos in [8, 9, 10]:
                            if pos < len(parts):
                                try:
                                    cpu_percent = float(parts[pos].replace('%', ''))
                                    total_cpu += cpu_percent
                                    break
                                except ValueError:
                                    continue

            return total_cpu if total_cpu > 0 else None

        except Exception as e:
            logger.error(f"Error getting CPU from top for {package_name}: {e}")
            return None

    def collect_app_metrics(self, package_names: List[str]) -> List[MetricPoint]:
        points = []
        current_time = datetime.now(timezone.utc)
        base_tags = {"device_serial": self.device_serial}

        for package_name in package_names:
            # Check if app is running
            ps_output = self.run_adb_command(f"ps | grep {package_name}")
            if not ps_output:
                continue

            app_tags = {**base_tags, "package_name": package_name}

            # Memory usage
            meminfo_output = self.run_adb_command(f"dumpsys meminfo {package_name}")
            if meminfo_output:
                pss_match = re.search(r"TOTAL\s+(\d+)", meminfo_output)
                if pss_match:
                    pss_memory = int(pss_match.group(1)) * 1024
                    points.append(
                        MetricPoint(
                            measurement="app_memory",
                            tags=app_tags,
                            fields={"pss_bytes": pss_memory},
                            timestamp=current_time,
                        )
                    )

            # CPU usage - try dumpsys first, then top as fallback
            cpu_usage = self._get_app_cpu_from_dumpsys(package_name)
            if cpu_usage is None:
                cpu_usage = self._get_app_cpu_from_top(package_name)

            if cpu_usage is not None and cpu_usage > 0:
                points.append(
                    MetricPoint(
                        measurement="app_cpu",
                        tags=app_tags,
                        fields={"usage_percent": cpu_usage},
                        timestamp=current_time,
                    )
                )

        return points

    def collect_all_metrics(self, app_patterns: Optional[List[str]]) -> List[MetricPoint]:
        all_points = []

        logger.info(f"Collecting metrics for device: {self.device_serial}")

        # Temperature metrics
        all_points.extend(self.collect_temperature_metrics())

        # Global system metrics
        all_points.extend(self.collect_global_system_metrics())

        # App-specific metrics
        if app_patterns:
            logger.info(f"Collecting metrics for app patterns: {app_patterns}")
            all_app_packages = []

            for pattern in app_patterns:
                packages = self.get_installed_packages(pattern)
                logger.info(f"Found {len(packages)} packages matching '{pattern}'")
                all_app_packages.extend(packages)

            # Remove duplicates
            all_app_packages = list(set(all_app_packages))

            if all_app_packages:
                logger.info(f"Collecting metrics for {len(all_app_packages)} unique apps")
                all_points.extend(self.collect_app_metrics(all_app_packages))
        else:
            logger.info("No app patterns specified, only collecting global metrics")

        return all_points
