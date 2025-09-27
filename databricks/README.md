# Databricks Workspace Automation

This directory contains Python scripts for managing Databricks workspaces and clusters programmatically.

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Setup**:
   - Copy `.env.example` to `.env` in this directory:
     ```bash
     cp .env.example .env
     ```
   - Update `.env` with your actual values:
     ```ini
     DATABRICKS_HOST=https://your-workspace.azuredatabricks.net
     DATABRICKS_TOKEN=your_personal_access_token
     ```

## Authentication

The scripts support two authentication methods (in order of priority):
1. **Personal Access Token (PAT)** - Recommended
   - Set `DATABRICKS_TOKEN` in `.env` or pass via `--token` flag
2. **Azure CLI** - Fallback
   - Requires `az login` with appropriate permissions

## Available Scripts

### 1. `manage_cluster_from_config.py`

Main script for cluster operations using `cluster_config.yaml`:

```bash
# Ensure cluster exists and is running (create if needed)
python manage_cluster_from_config.py --host $DATABRICKS_HOST ensure --wait

# Recreate cluster (delete if exists, then create)
python manage_cluster_from_config.py --host $DATABRICKS_HOST recreate --wait

# Stop cluster
python manage_cluster_from_config.py --host $DATABRICKS_HOST stop --wait

# Check cluster status
python manage_cluster_from_config.py --host $DATABRICKS_HOST status
```

### 2. `start_databricks_clusters.py`

Alternative script with more cluster management options:

```bash
# Start all non-running clusters
python start_databricks_clusters.py --all --wait

# Start specific cluster by name
python start_databricks_clusters.py --name "fixitfred-dev" --wait

# Stop all clusters (requires confirmation)
python start_databricks_clusters.py --all --stop-after-ready
```

### 3. `deploy_databricks_workspace.py`
Script for deploying and managing Databricks workspaces, including cluster setup and workspace configuration.

### 4. `stop_databricks_clusters.py`
Script for stopping Databricks clusters.

### 5. Helper Scripts
- `create_verify_stop_cluster.py`: Example workflow for cluster lifecycle
- `list_databricks_options.py`: List available cluster configurations
- `cluster_config.yaml`: Configuration for the default dev cluster (e.g., `fixitfred-dev`, Spark version, node type, workers, auto-termination minutes)

## Cost Management

- Clusters incur costs while running
- Default auto-termination: 15 minutes of inactivity
- Always stop clusters when not in use:
  ```bash
  python manage_cluster_from_config.py --host $DATABRICKS_HOST stop --wait
  ```

## Development

- **Testing**: Run `pytest` in the `databricks` directory
- **Linting**: `flake8 .` and `black .`
- **Formatting**: `black .` before committing

## Troubleshooting

- **Authentication Errors**:
  - Verify `DATABRICKS_TOKEN` is valid
  - Ensure Azure CLI is logged in if using that method
  - Check workspace URL in `DATABRICKS_HOST`

- **Cluster Issues**:
  - Check Databricks UI for detailed logs
  - Verify network connectivity to Databricks workspace
  - Ensure sufficient permissions in Databricks workspace

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
