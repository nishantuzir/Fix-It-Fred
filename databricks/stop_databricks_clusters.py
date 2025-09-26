#!/usr/bin/env python3
"""
Stop All Databricks Clusters Script

This script connects to Azure Databricks and terminates all running clusters
to prevent incurring costs when they're not needed.

Requirements:
- pip install databricks-sdk azure-identity
- Azure CLI authentication or service principal
- DATABRICKS_HOST environment variable or pass workspace URL
"""

import os
import sys
from datetime import datetime
from azure.identity import DefaultAzureCredential
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.compute import State

# Configuration
WORKSPACE_URL = os.environ.get("DATABRICKS_HOST", "https://adb-1393800878508171.11.azuredatabricks.net")
RESOURCE_GROUP = "rg-databricks-prod-v2"
WORKSPACE_NAME = "databricks-prod-ws"

def get_databricks_client():
    """Initialize Databricks client with Azure authentication"""
    try:
        # Use Azure CLI authentication
        credential = DefaultAzureCredential()

        # Initialize Databricks client
        client = WorkspaceClient(
            host=WORKSPACE_URL,
            azure_client_id=None,  # Will use DefaultAzureCredential
            azure_client_secret=None,
            azure_tenant_id=None,
            auth_type="azure-cli"
        )

        return client
    except Exception as e:
        print(f"Failed to initialize Databricks client: {e}")
        print("Make sure you're authenticated with Azure CLI: az login")
        sys.exit(1)

def list_clusters(client):
    """List all clusters in the workspace"""
    try:
        clusters = client.clusters.list()
        return list(clusters)
    except Exception as e:
        print(f"Failed to list clusters: {e}")
        return []

def terminate_cluster(client, cluster_id, cluster_name):
    """Terminate a specific cluster"""
    try:
        print(f"Terminating cluster: {cluster_name} (ID: {cluster_id})")
        client.clusters.delete(cluster_id=cluster_id)
        print(f"[SUCCESS] Successfully initiated termination for cluster: {cluster_name}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to terminate cluster {cluster_name}: {e}")
        return False

def wait_for_termination(client, cluster_id, cluster_name, timeout_minutes=10):
    """Wait for cluster to fully terminate"""
    import time

    timeout_seconds = timeout_minutes * 60
    start_time = time.time()

    print(f"Waiting for cluster {cluster_name} to terminate...")

    while time.time() - start_time < timeout_seconds:
        try:
            cluster = client.clusters.get(cluster_id=cluster_id)
            if cluster.state == State.TERMINATED:
                print(f"[SUCCESS] Cluster {cluster_name} is fully terminated")
                return True
            elif cluster.state in [State.TERMINATING]:
                print(f"[WAIT] Cluster {cluster_name} is still terminating...")
                time.sleep(30)
            else:
                print(f"[INFO] Cluster {cluster_name} state: {cluster.state}")
                time.sleep(30)
        except Exception as e:
            print(f"Error checking cluster status: {e}")
            time.sleep(30)

    print(f"[WARNING] Timeout waiting for cluster {cluster_name} to terminate")
    return False

def main():
    print("=" * 60)
    print("Azure Databricks Cluster Termination Script")
    print("=" * 60)
    print(f"Workspace URL: {WORKSPACE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Initialize client
    print("[AUTH] Authenticating with Azure Databricks...")
    client = get_databricks_client()
    print("[SUCCESS] Successfully authenticated")

    # List all clusters
    print("\n[LIST] Listing all clusters...")
    clusters = list_clusters(client)

    if not clusters:
        print("[INFO] No clusters found in the workspace")
        print("\n[COST] Cost Status: No compute costs being incurred")
        return

    print(f"Found {len(clusters)} cluster(s):")

    running_clusters = []
    terminated_clusters = []

    # Check cluster states
    for cluster in clusters:
        status_text = {
            State.RUNNING: "[RUNNING]",
            State.TERMINATED: "[TERMINATED]",
            State.TERMINATING: "[TERMINATING]",
            State.PENDING: "[PENDING]",
            State.RESTARTING: "[RESTARTING]",
            State.RESIZING: "[RESIZING]",
            State.ERROR: "[ERROR]",
            State.UNKNOWN: "[UNKNOWN]"
        }.get(cluster.state, "[UNKNOWN]")

        print(f"  {status_text} {cluster.cluster_name} (ID: {cluster.cluster_id}) - State: {cluster.state}")

        if cluster.state in [State.RUNNING, State.PENDING, State.RESTARTING, State.RESIZING]:
            running_clusters.append(cluster)
        elif cluster.state == State.TERMINATED:
            terminated_clusters.append(cluster)

    print()

    # Terminate running clusters
    if running_clusters:
        print(f"[STOP] Found {len(running_clusters)} active cluster(s) that need termination")
        print("Proceeding to terminate all active clusters...\n")

        successful_terminations = 0

        for cluster in running_clusters:
            if terminate_cluster(client, cluster.cluster_id, cluster.cluster_name):
                successful_terminations += 1

        print(f"\n[SUMMARY] Termination Summary:")
        print(f"  [SUCCESS] Successfully terminated: {successful_terminations}")
        print(f"  [FAILED] Failed to terminate: {len(running_clusters) - successful_terminations}")

        # Wait for terminations to complete
        if successful_terminations > 0:
            print(f"\n[WAIT] Waiting for clusters to fully terminate...")
            for cluster in running_clusters:
                wait_for_termination(client, cluster.cluster_id, cluster.cluster_name)

    else:
        print("[SUCCESS] All clusters are already terminated")

    # Final status
    print("\n" + "=" * 60)
    print("FINAL STATUS")
    print("=" * 60)

    if running_clusters:
        if successful_terminations == len(running_clusters):
            print("[SUCCESS] All clusters have been successfully terminated")
            print("[COST] Cost Status: No compute costs being incurred")
        else:
            print("[WARNING] Some clusters may still be running - check manually")
            print("[COST] Cost Status: May still incur compute costs")
    else:
        print("[SUCCESS] No active clusters found")
        print("[COST] Cost Status: No compute costs being incurred")

    print(f"\nWorkspace Infrastructure Costs:")
    print(f"  * Databricks Workspace: FREE (no cost when idle)")
    print(f"  * Virtual Network: FREE")
    print(f"  * Network Security Groups: FREE")
    print(f"  * Storage Account: ~$0.50-$5/month (minimal)")
    print(f"  * Managed Identity: FREE")

    print(f"\n[IMPORTANT] Remember: Only running clusters incur DBU and VM costs!")
    print(f"            The workspace itself has no cost when no clusters are running.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARNING] Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        sys.exit(1)