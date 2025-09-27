#!/usr/bin/env python3
"""
List Databricks workspace options (Spark versions and node types).

Usage:
  python databricks/list_databricks_options.py --host <workspace-url> --token <pat>

It uses PAT auth when --token is provided or DATABRICKS_TOKEN env is set.
"""
import argparse
import os
import sys
from databricks.sdk import WorkspaceClient


def get_client(host: str, token: str | None) -> WorkspaceClient:
    token = token or os.environ.get("DATABRICKS_TOKEN")
    if token:
        return WorkspaceClient(host=host, token=token)
    # Fallback to azure-cli if token not provided
    return WorkspaceClient(host=host, auth_type="azure-cli")


def main():
    p = argparse.ArgumentParser(description="List Spark versions and node types available in the workspace")
    p.add_argument("--host", required=True, help="Workspace host, e.g. https://adb-<id>.<region>.azuredatabricks.net")
    p.add_argument("--token", default=None, help="Personal Access Token (PAT)")
    args = p.parse_args()

    try:
        client = get_client(args.host, args.token)
    except Exception as e:
        print(f"[ERROR] Failed to authenticate: {e}")
        print("Provide a valid --token, or ensure Azure CLI is logged in (az login)")
        sys.exit(1)

    print("\n=== Spark Versions (first 15) ===")
    try:
        versions_resp = client.clusters.spark_versions()
        # SDK returns an object with .versions or an iterable; support both
        versions_list = None
        if hasattr(versions_resp, "versions") and versions_resp.versions is not None:
            versions_list = versions_resp.versions
        else:
            versions_list = list(versions_resp)  # may raise if not iterable

        out = [str(v) for v in versions_list]
        for v in out[:15]:
            print(" -", v)
        if len(out) == 0:
            print("(none)")
    except Exception as e:
        print(f"[ERROR] Could not list spark versions: {e}")

    print("\n=== Node Types (first 20) ===")
    try:
        node_types_resp = client.clusters.list_node_types()
        node_types = None
        if hasattr(node_types_resp, "node_types") and node_types_resp.node_types is not None:
            node_types = node_types_resp.node_types
        else:
            node_types = list(node_types_resp)
        # Each node_type may have attributes like node_type_id and memory_mb/vcpu_count
        count = 0
        for nt in node_types:
            nid = getattr(nt, "node_type_id", None) or getattr(nt, "node_type", None) or str(nt)
            mem = getattr(nt, "memory_mb", None)
            vcpu = getattr(nt, "num_cores", None) or getattr(nt, "vcpu_count", None)
            extras = []
            if mem is not None:
                extras.append(f"mem={mem}MB")
            if vcpu is not None:
                extras.append(f"vCPU={vcpu}")
            extra_s = (" (" + ", ".join(extras) + ")") if extras else ""
            print(f" - {nid}{extra_s}")
            count += 1
            if count >= 20:
                break
        if count == 0:
            print("(none)")
    except Exception as e:
        print(f"[ERROR] Could not list node types: {e}")


if __name__ == "__main__":
    main()
