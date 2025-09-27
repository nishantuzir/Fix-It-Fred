# Databricks Workspace Automation

This directory contains Python scripts for managing Databricks workspaces and clusters programmatically.

## Files

### 1. deploy_databricks_workspace.py
A Python script for deploying and managing Databricks workspaces. This script likely handles the creation and configuration of Databricks workspaces, including cluster setup, job creation, and workspace configuration.

### 2. stop_databricks_clusters.py
A utility script to stop all running Databricks clusters. This can be used for cost optimization by ensuring clusters are not left running when not in use.

### 3. start_databricks_clusters.py
A utility script to start Databricks clusters so the environment is ready for development or production. You can start all clusters, a specific cluster by ID, or by name, and optionally wait for them to reach RUNNING.

### 4. manage_cluster_from_config.py
Create, recreate, ensure, start, stop, or check status of a default cluster defined in `cluster_config.yaml`.

### 5. cluster_config.yaml
YAML file with the reusable defaults for the small dev cluster (e.g., `fixitfred-dev`, Spark version, node type, workers, auto-termination minutes).

### 6. .env
Environment configuration file containing sensitive information and configuration parameters required by the scripts. **Important**: Never commit sensitive information to version control. This file should be listed in .gitignore.

## Prerequisites

- Python 3.6+
- Databricks CLI configured with appropriate permissions
- Required Python packages (install using `pip install -r requirements.txt`)

## Setup

1. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and update the configuration:
   ```bash
   cp .env.example .env
   # Edit .env with your Databricks configuration
   ```

## Usage

### Deploy Databricks Workspace
```bash
python deploy_databricks_workspace.py
```

### Stop All Running Clusters
```bash
python stop_databricks_clusters.py
```

### Start Clusters
Use this to bring the Databricks layer online by starting compute.

```bash
# Start all non-running clusters (uses DATABRICKS_HOST from .env if set)
python start_databricks_clusters.py --all

# Start a specific cluster by ID
python start_databricks_clusters.py --cluster-id <cluster-id>

# Start a specific cluster by exact name
python start_databricks_clusters.py --name "My Interactive Cluster"

# Wait until clusters are RUNNING
python start_databricks_clusters.py --all --wait --timeout-minutes 20

# Dry-run (prints actions without making changes)
python start_databricks_clusters.py --all --dry-run

# Override workspace host if needed
python start_databricks_clusters.py --host https://<your-workspace>.azuredatabricks.net --all

#### Start then Stop (verification run)
Bring clusters online, wait until RUNNING, then stop them (useful for validation):

```bash
python start_databricks_clusters.py --all --stop-after-ready
```

### Manage Cluster from Config
The default dev cluster is parameterized in `cluster_config.yaml`. Use the following commands with PAT auth or Azure CLI auth:

```bash
# Create from config (fails if the cluster already exists)
python manage_cluster_from_config.py --host https://<workspace> --token <PAT> create --wait

# Recreate on demand (delete existing, then create)
python manage_cluster_from_config.py --host https://<workspace> --token <PAT> recreate --wait

# Ensure exists and running (create if missing; start if terminated)
python manage_cluster_from_config.py --host https://<workspace> --token <PAT> ensure --wait

# Start/Stop by name in config
python manage_cluster_from_config.py --host https://<workspace> --token <PAT> start --wait
python manage_cluster_from_config.py --host https://<workspace> --token <PAT> stop --wait

# Status
python manage_cluster_from_config.py --host https://<workspace> --token <PAT> status
```

## Security Note

- The `.env` file contains sensitive information and should never be committed to version control.
- Ensure proper permissions are set on the `.env` file.
- Consider using a secrets management solution for production environments.

## License

Copyright 2025 Nishant Uzir

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Contributing

Please feel free to submit a pull request or open an issue.
