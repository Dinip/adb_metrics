#!/bin/bash

# Check if .env file exists
ENV_FILE="../.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    echo "Please create one based on .env.example before running this script."
    exit 1
fi

# Read the environment variables from .env file without sourcing
echo "Reading environment variables from .env file..."
INFLUXDB_ORG=$(grep -E "^INFLUXDB_ORG=" "$ENV_FILE" | cut -d '=' -f2 | tr -d '"')
INFLUXDB_BUCKET=$(grep -E "^INFLUXDB_BUCKET=" "$ENV_FILE" | cut -d '=' -f2 | tr -d '"')
INFLUXDB_TOKEN=$(grep -E "^INFLUXDB_TOKEN=" "$ENV_FILE" | cut -d '=' -f2 | tr -d '"')

# Ensure required variables are present
if [ -z "$INFLUXDB_ORG" ] || [ -z "$INFLUXDB_BUCKET" ] || [ -z "$INFLUXDB_TOKEN" ]; then
    echo "Error: Required environment variables are missing in .env file."
    echo "Please ensure INFLUXDB_ORG, INFLUXDB_BUCKET, and INFLUXDB_TOKEN are defined."
    exit 1
fi

echo "Updating Grafana configuration files with environment variables..."

# Function to replace template variables in a file
replace_vars() {
    local file=$1
    echo "Processing file: $file"

    # Replace all occurrences of the template variables
    sed -i "s|\${{INFLUXDB_ORG}}|$INFLUXDB_ORG|g" "$file"
    sed -i "s|\${{INFLUXDB_BUCKET}}|$INFLUXDB_BUCKET|g" "$file"
    sed -i "s|\${{INFLUXDB_TOKEN}}|$INFLUXDB_TOKEN|g" "$file"
}

# Find all files recursively in the grafana directory
find "$(dirname "$0")" -type f -not -path "*/\.*" | while read -r file; do
    # Skip this script itself
    if [[ "$file" != *"update_references.sh"* ]]; then
        # Check if file contains any of the template variables
        if grep -q "\${{INFLUXDB_" "$file"; then
            replace_vars "$file"
        fi
    fi
done

echo "Configuration update complete!"
