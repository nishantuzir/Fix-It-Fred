# Databricks Workspace Automation

This directory contains Python scripts for managing Databricks workspaces and clusters programmatically.

## Files

### 1. deploy_databricks_workspace.py
A Python script for deploying and managing Databricks workspaces. This script likely handles the creation and configuration of Databricks workspaces, including cluster setup, job creation, and workspace configuration.

### 2. stop_databricks_clusters.py
A utility script to stop all running Databricks clusters. This can be used for cost optimization by ensuring clusters are not left running when not in use.

### 3. .env
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

## Security Note

- The `.env` file contains sensitive information and should never be committed to version control.
- Ensure proper permissions are set on the `.env` file.
- Consider using a secrets management solution for production environments.

## License

MIT License

## Contributing

Please feel free to submit a pull request or open an issue.

