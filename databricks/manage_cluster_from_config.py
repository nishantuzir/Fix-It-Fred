#!/usr/bin/env python3
"""
Manage the default Fix-It-Fred Databricks cluster from a YAML config.

Config file: databricks/cluster_config.yaml

Auth:
- Prefer PAT via --token or DATABRICKS_TOKEN env var
- Fallback to Azure CLI auth if PAT not provided

Examples:
  # Create from config (fails if already exists with same name)
  python databricks/manage_cluster_from_config.py --host https://<host> --token <pat> create

  # Recreate on demand (delete existing with same name, then create)
  python databricks/manage_cluster_from_config.py --host https://<host> --token <pat> recreate

  # Ensure exists and running (create if missing; start if terminated)
  python databricks/manage_cluster_from_config.py --host https://<host> --token <pat> ensure --wait

  # Start/Stop/Status by config name
  python databricks/manage_cluster_from_config.py --host https://<host> --token <pat> start --wait
  python databricks/manage_cluster_from_config.py --host https://<host> --token <pat> stop --wait
  python databricks/manage_cluster_from_config.py --host https://<host> --token <pat> status
"""
import argparse
import os
import sys
import time
from typing import Optional

import yaml
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.compute import State
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "cluster_config.yaml")


def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_client(host: str, token: Optional[str]) -> WorkspaceClient:
    token = token or os.environ.get("DATABRICKS_TOKEN")
    if token:
        return WorkspaceClient(host=host, token=token)
    return WorkspaceClient(host=host, auth_type="azure-cli")


def find_cluster_by_name(w: WorkspaceClient, name: str):
    try:
        clusters = list(w.clusters.list())
        for c in clusters:
            if c.cluster_name == name:
                return c
        return None
    except Exception as e:
        print(f"[ERROR] Failed to list clusters: {e}")
        return None


def wait_for_state(w: WorkspaceClient, cluster_id: str, target: State, timeout_min: int = 20) -> bool:
    deadline = time.time() + timeout_min * 60
    while time.time() < deadline:
        try:
            c = w.clusters.get(cluster_id=cluster_id)
            if c.state == target:
                print(f"[SUCCESS] Cluster {c.cluster_name} reached state: {target}")
                return True
            print(f"[WAIT] {c.cluster_name} state: {c.state} -> waiting for {target}; recheck in 20s")
            time.sleep(20)
        except Exception as e:
            print(f"[ERROR] Polling cluster state failed: {e}")
            time.sleep(20)
    print(f"[WARNING] Timeout waiting for cluster {cluster_id} to reach {target}")
    return False


def create_from_config(w: WorkspaceClient, cfg: dict) -> str:
    print("[CREATE] Creating cluster from config ...")
    res = w.clusters.create(
        cluster_name=cfg["name"],
        spark_version=cfg["spark_version_key"],
        node_type_id=cfg["node_type_id"],
        num_workers=int(cfg.get("workers", 1)),
        autotermination_minutes=int(cfg.get("autotermination_minutes", 15)),
        policy_id=cfg.get("policy_id"),
    )
    print(f"[SUCCESS] Create submitted. Cluster ID: {res.cluster_id}")
    return res.cluster_id


def cmd_create(w: WorkspaceClient, cfg: dict, wait: bool, timeout: int):
    existing = find_cluster_by_name(w, cfg["name"])
    if existing:
        print(f"[ERROR] Cluster '{cfg['name']}' already exists (ID: {existing.cluster_id})")
        sys.exit(1)
    cid = create_from_config(w, cfg)
    if wait:
        wait_for_state(w, cid, State.RUNNING, timeout)


def cmd_recreate(w: WorkspaceClient, cfg: dict, wait: bool, timeout: int):
    existing = find_cluster_by_name(w, cfg["name"])
    if existing:
        print(f"[DELETE] Deleting existing cluster '{cfg['name']}' (ID: {existing.cluster_id})")
        w.clusters.delete(cluster_id=existing.cluster_id)
        wait_for_state(w, existing.cluster_id, State.TERMINATED, max(10, timeout // 2))
    cid = create_from_config(w, cfg)
    if wait:
        wait_for_state(w, cid, State.RUNNING, timeout)


def cmd_ensure(w: WorkspaceClient, cfg: dict, wait: bool, timeout: int):
    existing = find_cluster_by_name(w, cfg["name"])
    if not existing:
        print("[ENSURE] Cluster not found; creating ...")
        cid = create_from_config(w, cfg)
        if wait:
            wait_for_state(w, cid, State.RUNNING, timeout)
        return
    print(f"[ENSURE] Found cluster '{cfg['name']}' (ID: {existing.cluster_id}) state={existing.state}")
    if existing.state in [State.TERMINATED, State.ERROR]:
        print("[START] Starting cluster ...")
        w.clusters.start(cluster_id=existing.cluster_id)
        if wait:
            wait_for_state(w, existing.cluster_id, State.RUNNING, timeout)
    elif existing.state in [State.RUNNING, State.RESIZING, State.RESTARTING, State.PENDING]:
        print("[ENSURE] Cluster already starting/running; no action taken")
    else:
        print(f"[ENSURE] Unhandled state: {existing.state}")


def cmd_start(w: WorkspaceClient, cfg: dict, wait: bool, timeout: int):
    existing = find_cluster_by_name(w, cfg["name"])
    if not existing:
        print("[ERROR] Cluster not found; use 'ensure' or 'create' first")
        sys.exit(1)
    if existing.state == State.RUNNING:
        print("[SKIP] Cluster already RUNNING")
        return
    w.clusters.start(cluster_id=existing.cluster_id)
    if wait:
        wait_for_state(w, existing.cluster_id, State.RUNNING, timeout)


def cmd_stop(w: WorkspaceClient, cfg: dict, wait: bool, timeout: int):
    existing = find_cluster_by_name(w, cfg["name"])
    if not existing:
        print("[ERROR] Cluster not found")
        sys.exit(1)
    w.clusters.delete(cluster_id=existing.cluster_id)
    if wait:
        wait_for_state(w, existing.cluster_id, State.TERMINATED, timeout)


def cmd_status(w: WorkspaceClient, cfg: dict):
    existing = find_cluster_by_name(w, cfg["name"])
    if not existing:
        print("[STATUS] Cluster not found")
        return
    print(f"[STATUS] {existing.cluster_name} (ID: {existing.cluster_id}) state={existing.state}")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Manage default cluster from YAML config")
    ap.add_argument("command", choices=["create", "recreate", "ensure", "start", "stop", "status"], help="Action")
    ap.add_argument("--host", required=True, help="Workspace host URL")
    ap.add_argument("--token", default=None, help="Databricks PAT (or set DATABRICKS_TOKEN)")
    ap.add_argument("--config", default=CONFIG_PATH, help="Path to cluster_config.yaml")
    ap.add_argument("--wait", action="store_true", help="Wait for target states")
    ap.add_argument("--timeout-minutes", type=int, default=20, help="Timeout for waits")
    return ap.parse_args()


def main():
    args = parse_args()
    try:
        cfg = load_config(args.config)
    except Exception as e:
        print(f"[ERROR] Failed to read config {args.config}: {e}")
        sys.exit(1)

    try:
        w = get_client(args.host, args.token)
    except Exception as e:
        print(f"[ERROR] Authentication failed: {e}")
        sys.exit(1)

    if args.command == "create":
        cmd_create(w, cfg, args.wait, args.timeout_minutes)
    elif args.command == "recreate":
        cmd_recreate(w, cfg, args.wait, args.timeout_minutes)
    elif args.command == "ensure":
        cmd_ensure(w, cfg, args.wait, args.timeout_minutes)
    elif args.command == "start":
        cmd_start(w, cfg, args.wait, args.timeout_minutes)
    elif args.command == "stop":
        cmd_stop(w, cfg, args.wait, args.timeout_minutes)
    elif args.command == "status":
        cmd_status(w, cfg)


if __name__ == "__main__":
    main()
