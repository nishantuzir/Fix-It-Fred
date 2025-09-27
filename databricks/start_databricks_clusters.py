#!/usr/bin/env python3
"""
Start Databricks Clusters Script

This script connects to Azure Databricks and starts clusters so the
"Databricks layer" is up and running for development or production use.

Features:
- Start all clusters that are not RUNNING
- Start a specific cluster by ID or by name
- Wait for clusters to reach RUNNING state
- Dry-run mode for safe previews

Requirements:
- pip install -r databricks/requirements.txt
- Azure CLI authentication or service principal
- DATABRICKS_HOST environment variable or pass via --host

Examples:
  python databricks/start_databricks_clusters.py --all
  python databricks/start_databricks_clusters.py --cluster-id abc-123
  python databricks/start_databricks_clusters.py --name "My Interactive Cluster"
  python databricks/start_databricks_clusters.py --all --dry-run
"""

import os
import sys
import time
import argparse
from datetime import datetime
from typing import List, Optional

from azure.identity import DefaultAzureCredential  # noqa: F401 (for parity & future use)
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.compute import State, ClusterDetails
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Defaults (same style as stop_databricks_clusters.py)
DEFAULT_WORKSPACE_URL = os.environ.get(
    "DATABRICKS_HOST",
    "https://adb-1393800878508171.11.azuredatabricks.net",
)


# -----------------------------
# Client helpers
# -----------------------------

def get_databricks_client(host: Optional[str], token: Optional[str] = None) -> WorkspaceClient:
    """Initialize Databricks client.

    Auth preference:
    1) PAT token if provided via --token or DATABRICKS_TOKEN
    2) Azure CLI (auth_type="azure-cli")
    """
    target_host = host or DEFAULT_WORKSPACE_URL
    token = token or os.environ.get("DATABRICKS_TOKEN")
    try:
        if token:
            # PAT-based auth
            client = WorkspaceClient(host=target_host, token=token)
        else:
            # Azure CLI-based auth
            client = WorkspaceClient(
                host=target_host,
                auth_type="azure-cli",
            )
        return client
    except Exception as e:
        print(f"[ERROR] Failed to initialize Databricks client: {e}")
        if not token:
            print("Tip: You can set a PAT in DATABRICKS_TOKEN or pass --token <token> to avoid Azure CLI dependency.")
            print("Otherwise, make sure you're authenticated with Azure CLI: az login")
        sys.exit(1)


def list_clusters(client: WorkspaceClient) -> List[ClusterDetails]:
    """List all clusters in the workspace."""
    try:
        clusters = client.clusters.list()
        return list(clusters)
    except Exception as e:
        print(f"[ERROR] Failed to list clusters: {e}")
        return []


# -----------------------------
# Cluster operations
# -----------------------------

def start_cluster(client: WorkspaceClient, cluster_id: str, cluster_name: str, dry_run: bool = False) -> bool:
    """Start a specific cluster by ID."""
    try:
        if dry_run:
            print(f"[DRY-RUN] Would start cluster: {cluster_name} (ID: {cluster_id})")
            return True
        print(f"[START] Starting cluster: {cluster_name} (ID: {cluster_id})")
        client.clusters.start(cluster_id=cluster_id)
        print(f"[SUCCESS] Start request submitted for: {cluster_name}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to start cluster {cluster_name}: {e}")
        return False


def wait_for_running(
    client: WorkspaceClient,
    cluster_id: str,
    cluster_name: str,
    timeout_minutes: int = 15,
) -> bool:
    """Wait for a cluster to reach RUNNING state."""
    timeout_seconds = timeout_minutes * 60
    start_time = time.time()

    print(f"[WAIT] Waiting for cluster {cluster_name} to be RUNNING...")

    while time.time() - start_time < timeout_seconds:
        try:
            cluster = client.clusters.get(cluster_id=cluster_id)
            if cluster.state == State.RUNNING:
                print(f"[SUCCESS] Cluster {cluster_name} is RUNNING")
                return True
            elif cluster.state in [State.PENDING, State.RESIZING, State.RESTARTING]:
                print(f"[WAIT] {cluster_name} state: {cluster.state} ... rechecking in 20s")
                time.sleep(20)
            elif cluster.state == State.TERMINATED:
                print(f"[WARNING] {cluster_name} returned to TERMINATED. Investigate cluster logs.")
                return False
            elif cluster.state == State.ERROR:
                print(f"[ERROR] {cluster_name} in ERROR state. Check event logs in Databricks UI.")
                return False
            else:
                print(f"[INFO] {cluster_name} state: {cluster.state} ... rechecking in 20s")
                time.sleep(20)
        except Exception as e:
            print(f"[ERROR] Checking cluster status failed: {e}")
            time.sleep(20)

    print(f"[WARNING] Timeout waiting for cluster {cluster_name} to be RUNNING")
    return False


# -----------------------------
# Stop operations
# -----------------------------
def stop_cluster(client: WorkspaceClient, cluster_id: str, cluster_name: str, dry_run: bool = False) -> bool:
    """Terminate a specific cluster."""
    try:
        if dry_run:
            print(f"[DRY-RUN] Would stop cluster: {cluster_name} (ID: {cluster_id})")
            return True
        print(f"[STOP] Stopping cluster: {cluster_name} (ID: {cluster_id})")
        client.clusters.delete(cluster_id=cluster_id)
        print(f"[SUCCESS] Stop request submitted for: {cluster_name}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to stop cluster {cluster_name}: {e}")
        return False


def wait_for_termination(
    client: WorkspaceClient,
    cluster_id: str,
    cluster_name: str,
    timeout_minutes: int = 10,
) -> bool:
    """Wait for a cluster to fully terminate."""
    timeout_seconds = timeout_minutes * 60
    start_time = time.time()

    print(f"[WAIT] Waiting for cluster {cluster_name} to TERMINATE...")

    while time.time() - start_time < timeout_seconds:
        try:
            cluster = client.clusters.get(cluster_id=cluster_id)
            if cluster.state == State.TERMINATED:
                print(f"[SUCCESS] Cluster {cluster_name} is TERMINATED")
                return True
            elif cluster.state in [State.TERMINATING]:
                print(f"[WAIT] {cluster_name} is TERMINATING ... rechecking in 20s")
                time.sleep(20)
            else:
                print(f"[INFO] {cluster_name} state: {cluster.state} ... rechecking in 20s")
                time.sleep(20)
        except Exception as e:
            print(f"[ERROR] Checking termination status failed: {e}")
            time.sleep(20)

    print(f"[WARNING] Timeout waiting for cluster {cluster_name} to TERMINATE")
    return False


# -----------------------------
# Selection helpers
# -----------------------------

def select_clusters(
    clusters: List[ClusterDetails],
    cluster_id: Optional[str],
    name: Optional[str],
    all_flag: bool,
) -> List[ClusterDetails]:
    """Filter clusters based on CLI selection criteria."""
    if cluster_id:
        return [c for c in clusters if c.cluster_id == cluster_id]
    if name:
        return [c for c in clusters if c.cluster_name == name]
    if all_flag:
        return clusters
    # Default: non-running clusters only
    return [
        c
        for c in clusters
        if c.state not in [State.RUNNING, State.RESIZING, State.RESTARTING]
    ]


# -----------------------------
# CLI
# -----------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start Azure Databricks clusters so the environment is ready.",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Databricks workspace URL. Defaults to DATABRICKS_HOST or a pre-set sample URL.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Start all clusters.")
    group.add_argument("--cluster-id", help="Start only the cluster with this ID.")
    group.add_argument("--name", help="Start only the cluster with this exact name.")

    parser.add_argument(
        "--token",
        default=None,
        help="Databricks Personal Access Token (PAT). If omitted, will use DATABRICKS_TOKEN env or Azure CLI.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for clusters to reach RUNNING state.",
    )
    parser.add_argument(
        "--stop-after-ready",
        action="store_true",
        help="After confirming clusters are RUNNING (implies --wait), stop them.",
    )
    parser.add_argument(
        "--timeout-minutes",
        type=int,
        default=15,
        help="Timeout for --wait (per cluster). Default: 15",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not make changes; only print what would happen.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 60)
    print("Azure Databricks Cluster Start Script")
    print("=" * 60)
    print(f"Workspace URL: {args.host or DEFAULT_WORKSPACE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Initialize client
    print("[AUTH] Authenticating with Azure Databricks...")
    client = get_databricks_client(args.host, args.token)
    print("[SUCCESS] Successfully authenticated")

    # List clusters
    print("\n[LIST] Fetching clusters...")
    clusters = list_clusters(client)
    if not clusters:
        print("[INFO] No clusters found in the workspace")
        return

    # Select target clusters per args
    targets = select_clusters(clusters, args.cluster_id, args.name, args.all)
    if not targets:
        print("[INFO] No clusters matched the selection criteria.")
        return

    print(f"[INFO] Selected {len(targets)} cluster(s) to start:")
    for c in targets:
        print(f"  - {c.cluster_name} (ID: {c.cluster_id}) - Current state: {c.state}")

    # Start clusters
    print()
    successes = 0
    for c in targets:
        if c.state == State.RUNNING:
            print(f"[SKIP] {c.cluster_name} already RUNNING")
            # If asked to stop-after-ready and already RUNNING, honor stop as well
            if args.stop_after_ready and not args.dry_run:
                if stop_cluster(client, c.cluster_id, c.cluster_name, args.dry_run):
                    wait_for_termination(client, c.cluster_id, c.cluster_name)
            continue
        if start_cluster(client, c.cluster_id, c.cluster_name, args.dry_run):
            successes += 1
            # If stop-after-ready is set, we must ensure the cluster reaches RUNNING first
            if (args.wait or args.stop_after_ready) and not args.dry_run:
                ready = wait_for_running(client, c.cluster_id, c.cluster_name, args.timeout_minutes)
                if args.stop_after_ready and ready:
                    if stop_cluster(client, c.cluster_id, c.cluster_name, args.dry_run):
                        wait_for_termination(client, c.cluster_id, c.cluster_name)

    # Final status
    print("\n" + "=" * 60)
    print("FINAL STATUS")
    print("=" * 60)
    print(f"[SUMMARY] Start requests succeeded for {successes} / {len(targets)} cluster(s)")
    if args.dry_run:
        print("[NOTE] Dry-run mode: No actual start requests were sent.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARNING] Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        sys.exit(1)
