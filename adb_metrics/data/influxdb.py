#!/usr/bin/env python3

import logging
from typing import List

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from adb_metrics.config.config import config
from adb_metrics.device.android_metrics_collector import MetricPoint

logger = logging.getLogger(__name__)


class InfluxDBPersistence:
    def __init__(self, custom_config: dict = None):
        influx_config = custom_config or config.get_influxdb_config()

        try:
            self.client = InfluxDBClient(
                url=influx_config["url"],
                token=influx_config["token"],
                org=influx_config["org"]
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.bucket = influx_config["bucket"]

            # Test connection
            self.client.ping()
            logger.info(f"Successfully connected to InfluxDB at {influx_config['url']}")

        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            logger.error(f"URL: {influx_config['url']}")
            logger.error(f"Org: {influx_config['org']}")
            logger.error(f"Bucket: {influx_config['bucket']}")
            raise

    @staticmethod
    def _convert_metric_to_point(metric: MetricPoint) -> Point:
        point = Point(metric.measurement).time(metric.timestamp)

        for tag_key, tag_value in metric.tags.items():
            point = point.tag(tag_key, tag_value)

        for field_key, field_value in metric.fields.items():
            point = point.field(field_key, field_value)

        return point

    def write_metrics(self, metrics: List[MetricPoint]) -> bool:
        if not metrics:
            return True

        try:
            points = [self._convert_metric_to_point(metric) for metric in metrics]
            self.write_api.write(bucket=self.bucket, record=points)
            logger.info(f"Successfully wrote {len(points)} data points to InfluxDB")
            return True
        except Exception as e:
            logger.error(f"Error writing to InfluxDB: {e}")
            return False

    def close(self):
        self.client.close()


class ConsolePrinter:
    @staticmethod
    def print_metrics(metrics: List[MetricPoint]):
        if not metrics:
            print("No metrics collected")
            return

        print(f"\n=== Metrics Collection Report ({len(metrics)} points) ===")

        # Group by measurement type
        by_measurement = {}
        for metric in metrics:
            if metric.measurement not in by_measurement:
                by_measurement[metric.measurement] = []
            by_measurement[metric.measurement].append(metric)

        for measurement, points in by_measurement.items():
            print(f"\n📊 {measurement.upper()}:")
            for point in points:
                tags_str = ", ".join([f"{k}={v}" for k, v in point.tags.items()])
                fields_str = ", ".join([f"{k}={v:.2f}" for k, v in point.fields.items()])
                print(f"  [{tags_str}] {fields_str}")
