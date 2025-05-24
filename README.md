# ADB Metrics Collector

A tool for collecting and monitoring Android device and application metrics via ADB.

## Features

- **Device Monitoring:** Collect metrics from a single device or all connected devices
- **Global Metrics:** Monitor system-wide metrics like CPU, memory, and temperature
- **App-Specific Metrics:** Track resource usage of specific Android applications
- **Multiple Output Options:** Print to console or persist to InfluxDB
- **Pattern Matching:** Target apps using wildcard patterns
- **Multi-Pattern Support:** Monitor multiple app patterns simultaneously

## Installation (Local Development/Run)

1. Clone the repository
   ```bash
   git clone https://github.com/Dinip/adb_metrics.git
   cd adb_metrics
   ```

2. Install the required dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the example environment file to `.env` and configure it
   ```bash
   cp .env.example .env
   ```

4. Ensure ADB is installed and available in your PATH

## Configuration

The tool can be configured via:

- Environment variables
- `.env` file in the project root
- Command line arguments

### Environment Variables

```
ADB_HOST="localhost"
ADB_PORT="5037"
INFLUXDB_URL="http://localhost:8086"
INFLUXDB_TOKEN="admin_token"
INFLUXDB_ORG="adb_monitoring"
INFLUXDB_BUCKET="device_metrics"

# Needed for InfluxDB 2 initial setup.
# Remove if using already existing InfluxDB 2 instance.
# Make sure you set secure password and admin token for production use.
# Update docker-compose-prod.yml as needed.
INFLUXDB_USERNAME="admin"
INFLUXDB_PASSWORD="password"
INFLUXDB_ADMIN_TOKEN="admin_token"
```

### Grafana Configuration

The project includes pre-configured Grafana dashboards to visualize your Android device metrics.

1. Make sure your `.env` file is properly configured with your InfluxDB settings:
   ```
   INFLUXDB_ORG=your-organization
   INFLUXDB_BUCKET=android_metrics
   INFLUXDB_ADMIN_TOKEN=your-admin-token
   ```

2. Run the update references script to configure Grafana files with your environment settings:
   ```bash
   cd grafana
   chmod +x update_references.sh  # Make the script executable (Linux/macOS only)
   ./update_references.sh         # Linux/macOS
   # or
   bash update_references.sh      # Windows with Git Bash or WSL
   ```

3. The script will replace template variables in the Grafana configuration files with your actual values from the `.env`
   file.

4. Start Grafana with the provided configuration using docker-compose:
   ```bash
   docker-compose up -d
   ```

5. Access Grafana at http://localhost:3000 to view your Android device metrics dashboard.

## Usage

### Commands

```bash
# Show current configuration
python -m adb_metrics.main config

# List connected devices
python -m adb_metrics.main devices

# Print global metrics only (no app-specific metrics)
python -m adb_metrics.main print

# Print metrics for specific app pattern
python -m adb_metrics.main print --app-pattern "*.bmw.*"

# Print metrics for multiple app patterns
python -m adb_metrics.main print --app-pattern "*.bmw.*" --app-pattern "*.microsoft.*"

# Persist metrics to InfluxDB (global metrics only)
python -m adb_metrics.main persist --interval 10

# Persist metrics for specific device and app pattern
python -m adb_metrics.main persist --device-id ABCD1234WXYZ --app-pattern "*.bmw.*" --interval 5
```

#### Specify Custom ADB Host and Port

```bash
# Use ADB on a remote machine
python -m adb_metrics.main print --adb-host 192.168.1.100 --adb-port 5037
```

#### Monitor Specific Device

```bash
# List available devices first
python -m adb_metrics.main devices

# Then monitor a specific device by its ID
python -m adb_metrics.main print --device-id ABCD1234WXYZ
```

## Collected Metrics

### Global Metrics

- **System CPU Usage:**
    - User, system, idle percentages
    - Total CPU usage percentage

- **System Memory:**
    - Total memory
    - Used memory
    - Available memory
    - Memory usage percentage

- **Temperature:**
    - Battery temperature
    - Available thermal sensors

### Application-Specific Metrics

When app patterns are provided, these additional metrics are collected:

- **App CPU Usage:**
    - CPU usage percentage per application

- **App Memory:**
    - PSS memory usage in bytes

## Development

### Structure

- `adb_metrics/main.py` - Entry point and CLI interface
- `adb_metrics/device/` - Device interaction and metrics collection
- `adb_metrics/data/` - Data persistence logic
- `adb_metrics/config/` - Configuration management

## License

MIT License
