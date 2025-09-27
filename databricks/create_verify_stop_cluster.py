#!/usr/bin/env python3
"""
Create a lightweight interactive Databricks cluster, wait until RUNNING,
then terminate it. Useful to validate that the "Databricks layer" can start.

Usage:
  python databricks/create_verify_stop_cluster.py \
    --host https://adb-<id>.<region>.azuredatabricks.net \
    --token <PAT> \
    [--name fixitfred-dev] [--workers 1] [--autoterm 15]

Optional:
  --spark-version-key <key>   # otherwise first available LTS/Photon is chosen
  --node-type <id>            # otherwise a small DSv2/Dasv4 type is chosen
"""
import argparse
import os
import sys
import time
from dataclasses import dataclass
from typing import Optional

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.compute import State


@dataclass
class ClusterChoice:
    spark_version_key: str
    node_type_id: str


def _get_client(host: str, token: Optional[str]) -> WorkspaceClient:
    token = token or os.environ.get("DATABRICKS_TOKEN")
    if token:
        return WorkspaceClient(host=host, token=token)
    return WorkspaceClient(host=host, auth_type="azure-cli")


def choose_defaults(w: WorkspaceClient) -> ClusterChoice:
    # Spark version: prefer something with "LTS" or latest key
    versions_resp = w.clusters.spark_versions()
    versions = None
    if hasattr(versions_resp, "versions") and versions_resp.versions is not None:
        versions = versions_resp.versions
    else:
        versions = list(versions_resp)
    # versions may be objects or strings; get str and look for 'LTS' or 'Photon'
    sv_key = None
    str_keys = []
    for v in versions:
        s = getattr(v, "key", None) or str(v)
        str_keys.append(s)
    # prefer 16.x LTS or LTS generally
    for s in str_keys:
        if "LTS" in s or "lts" in s.lower():
            sv_key = s if "=" not in s else s.split("=")[-1]
            break
    if not sv_key and str_keys:
        sv_key = str_keys[0]

    # Node type: prefer small DS/Das sizes
    node_types_resp = w.clusters.list_node_types()
    node_types = node_types_resp.node_types if hasattr(node_types_resp, "node_types") else list(node_types_resp)
    preferred_prefixes = ("Standard_DS3", "Standard_D4s_v3", "Standard_DS3_v2", "Standard_D4a_v4", "Standard_D4as_v4")
    node_type_id = None
    for nt in node_types:
        nid = getattr(nt, "node_type_id", None) or getattr(nt, "node_type", None) or str(nt)
        if any(nid.startswith(p) for p in preferred_prefixes):
            node_type_id = nid
            break
    if not node_type_id and node_types:
        node_type_id = getattr(node_types[0], "node_type_id", None) or str(node_types[0])

    if not sv_key or not node_type_id:
        raise RuntimeError("Could not determine default spark version or node type")

    return ClusterChoice(spark_version_key=sv_key, node_type_id=node_type_id)


def wait_for_state(w: WorkspaceClient, cluster_id: str, target: State, timeout_min: int = 20) -> bool:
    deadline = time.time() + timeout_min * 60
    name = None
    while time.time() < deadline:
        try:
            c = w.clusters.get(cluster_id=cluster_id)
            name = name or c.cluster_name
            if c.state == target:
                print(f"[SUCCESS] Cluster {name} reached state: {target}")
                return True
            print(f"[WAIT] {name or cluster_id} state: {c.state} -> waiting for {target}; recheck in 20s")
            time.sleep(20)
        except Exception as e:
            print(f"[ERROR] Polling cluster state failed: {e}")
            time.sleep(20)
    print(f"[WARNING] Timeout waiting for cluster {name or cluster_id} to reach {target}")
    return False


def main():
    ap = argparse.ArgumentParser(description="Create a small cluster, wait for RUNNING, then TERMINATE")
    ap.add_argument("--host", required=True, help="Workspace host URL")
    ap.add_argument("--token", default=None, help="Databricks PAT")
    ap.add_argument("--name", default="fixitfred-dev", help="Cluster name")
    ap.add_argument("--workers", type=int, default=1, help="Number of workers")
    ap.add_argument("--autoterm", type=int, default=15, help="Auto-termination minutes")
    ap.add_argument("--spark-version-key", default=None, help="Spark version key")
    ap.add_argument("--node-type", default=None, help="Node type id")
    args = ap.parse_args()

    w = _get_client(args.host, args.token)

    # Resolve choices
    if args.spark_version_key and args.node_type:
        choice = ClusterChoice(spark_version_key=args.spark_version_key, node_type_id=args.node_type)
    else:
        choice = choose_defaults(w)

    print("Chosen options:")
    print(" - spark_version:", choice.spark_version_key)
    print(" - node_type_id:", choice.node_type_id)

    print("\n[CREATE] Creating cluster ...")
    try:
        create_res = w.clusters.create(
            cluster_name=args.name,
            spark_version=choice.spark_version_key,
            node_type_id=choice.node_type_id,
            num_workers=args.workers,
            autotermination_minutes=args.autoterm,
        )
        cluster_id = create_res.cluster_id
        print(f"[SUCCESS] Create request submitted. Cluster ID: {cluster_id}")
    except Exception as e:
        print(f"[ERROR] Could not create cluster: {e}")
        sys.exit(1)

    # Wait for running
    print("\n[WAIT] Waiting for cluster to reach RUNNING ...")
    ready = wait_for_state(w, cluster_id, State.RUNNING, timeout_min=30)

    # Stop regardless (cleanup), but report readiness status
    print("\n[STOP] Terminating the cluster ...")
    try:
        w.clusters.delete(cluster_id=cluster_id)
    except Exception as e:
        print(f"[ERROR] Failed to submit terminate: {e}")

    # Optionally wait until TERMINATED for completeness (short wait)
    wait_for_state(w, cluster_id, State.TERMINATED, timeout_min=20)

    if ready:
        print("\n[RESULT] Validation successful: cluster reached RUNNING and was terminated.")
        sys.exit(0)
    else:
        print("\n[RESULT] Cluster did not reach RUNNING before termination. Check events in the UI.")
        sys.exit(2)


if __name__ == "__main__":
    main()
