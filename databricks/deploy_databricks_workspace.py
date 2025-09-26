"""
Production-ready Azure Databricks workspace deployment with VNet injection.
- Requires: AZURE_SUBSCRIPTION_ID in env
- Auth: DefaultAzureCredential (Azure CLI / env / managed identity)
- Installs: pip install azure-identity azure-mgmt-resource
"""

import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import Deployment, DeploymentMode
from dotenv import load_dotenv

load_dotenv()
# ------------------------
# Config / defaults
# ------------------------
SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID")
if not SUBSCRIPTION_ID:
    raise SystemExit("Set AZURE_SUBSCRIPTION_ID environment variable before running.")

LOCATION = os.environ.get("AZURE_LOCATION", "")
RESOURCE_GROUP = os.environ.get("AZURE_RESOURCE_GROUP", "")
DEPLOYMENT_NAME = os.environ.get("AZURE_DEPLOYMENT_NAME", "")
VNET_NAME = os.environ.get("AZURE_VNET_NAME", "")
VNET_PREFIX = os.environ.get("AZURE_VNET_PREFIX", "")
PUBLIC_SUBNET_NAME = os.environ.get("AZURE_PUBLIC_SUBNET_NAME", "")
PUBLIC_SUBNET_PREFIX = os.environ.get("AZURE_PUBLIC_SUBNET_PREFIX", "")
PRIVATE_SUBNET_NAME = os.environ.get("AZURE_PRIVATE_SUBNET_NAME", "")
PRIVATE_SUBNET_PREFIX = os.environ.get("AZURE_PRIVATE_SUBNET_PREFIX", "")
WORKSPACE_NAME = os.environ.get("DATABRICKS_WORKSPACE_NAME", "")

# ------------------------
# Minimal ARM template
# ------------------------
arm_template = {
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {
        "workspaceName": {"type": "string"},
        "location": {"type": "string"},
        "vnetName": {"type": "string"},
        "vnetPrefix": {"type": "string"},
        "publicSubnetName": {"type": "string"},
        "publicSubnetPrefix": {"type": "string"},
        "privateSubnetName": {"type": "string"},
        "privateSubnetPrefix": {"type": "string"}
    },
    "variables": {
        "nsgName": "[concat(parameters('vnetName'), '-nsg')]"
    },
    "resources": [
        {
            "type": "Microsoft.Network/networkSecurityGroups",
            "apiVersion": "2021-05-01",
            "name": "[variables('nsgName')]",
            "location": "[parameters('location')]",
            "properties": {
                "securityRules": [
                    {
                        "name": "databricks-worker-to-databricks-webapp",
                        "properties": {
                            "description": "Required for worker communication with Databricks webapp",
                            "protocol": "Tcp",
                            "sourcePortRange": "*",
                            "destinationPortRanges": ["443", "3306", "8443", "8444", "8445", "8446", "8447", "8448", "8449", "8450", "8451"],
                            "sourceAddressPrefix": "VirtualNetwork",
                            "destinationAddressPrefix": "AzureDatabricks",
                            "access": "Allow",
                            "priority": 100,
                            "direction": "Outbound"
                        }
                    },
                    {
                        "name": "databricks-worker-to-sql",
                        "properties": {
                            "description": "Required for worker communication with SQL services",
                            "protocol": "Tcp",
                            "sourcePortRange": "*",
                            "destinationPortRange": "3306",
                            "sourceAddressPrefix": "VirtualNetwork",
                            "destinationAddressPrefix": "Sql",
                            "access": "Allow",
                            "priority": 101,
                            "direction": "Outbound"
                        }
                    },
                    {
                        "name": "databricks-worker-to-storage",
                        "properties": {
                            "description": "Required for worker communication with storage",
                            "protocol": "Tcp",
                            "sourcePortRange": "*",
                            "destinationPortRange": "443",
                            "sourceAddressPrefix": "VirtualNetwork",
                            "destinationAddressPrefix": "Storage",
                            "access": "Allow",
                            "priority": 102,
                            "direction": "Outbound"
                        }
                    },
                    {
                        "name": "databricks-worker-to-eventhub",
                        "properties": {
                            "description": "Required for worker communication with EventHub",
                            "protocol": "Tcp",
                            "sourcePortRange": "*",
                            "destinationPortRange": "9093",
                            "sourceAddressPrefix": "VirtualNetwork",
                            "destinationAddressPrefix": "EventHub",
                            "access": "Allow",
                            "priority": 103,
                            "direction": "Outbound"
                        }
                    },
                    {
                        "name": "databricks-control-plane-to-worker-ssh",
                        "properties": {
                            "description": "Required for control plane SSH to workers",
                            "protocol": "Tcp",
                            "sourcePortRange": "*",
                            "destinationPortRange": "22",
                            "sourceAddressPrefix": "AzureDatabricks",
                            "destinationAddressPrefix": "VirtualNetwork",
                            "access": "Allow",
                            "priority": 104,
                            "direction": "Inbound"
                        }
                    },
                    {
                        "name": "databricks-control-plane-to-worker-proxy",
                        "properties": {
                            "description": "Required for control plane proxy to workers",
                            "protocol": "Tcp",
                            "sourcePortRange": "*",
                            "destinationPortRange": "5557",
                            "sourceAddressPrefix": "AzureDatabricks",
                            "destinationAddressPrefix": "VirtualNetwork",
                            "access": "Allow",
                            "priority": 105,
                            "direction": "Inbound"
                        }
                    }
                ]
            }
        },
        {
            "type": "Microsoft.Network/virtualNetworks",
            "apiVersion": "2021-05-01",
            "name": "[parameters('vnetName')]",
            "location": "[parameters('location')]",
            "dependsOn": [
                "[resourceId('Microsoft.Network/networkSecurityGroups', variables('nsgName'))]"
            ],
            "properties": {
                "addressSpace": {
                    "addressPrefixes": ["[parameters('vnetPrefix')]"]
                },
                "subnets": [
                    {
                        "name": "[parameters('publicSubnetName')]",
                        "properties": {
                            "addressPrefix": "[parameters('publicSubnetPrefix')]",
                            "networkSecurityGroup": {
                                "id": "[resourceId('Microsoft.Network/networkSecurityGroups', variables('nsgName'))]"
                            },
                            "delegations": [
                                {
                                    "name": "databricks-delegation-public",
                                    "properties": {
                                        "serviceName": "Microsoft.Databricks/workspaces"
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "name": "[parameters('privateSubnetName')]",
                        "properties": {
                            "addressPrefix": "[parameters('privateSubnetPrefix')]",
                            "networkSecurityGroup": {
                                "id": "[resourceId('Microsoft.Network/networkSecurityGroups', variables('nsgName'))]"
                            },
                            "delegations": [
                                {
                                    "name": "databricks-delegation-private",
                                    "properties": {
                                        "serviceName": "Microsoft.Databricks/workspaces"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        },
        {
            "type": "Microsoft.Databricks/workspaces",
            "apiVersion": "2024-05-01",
            "name": "[parameters('workspaceName')]",
            "location": "[parameters('location')]",
            "sku": {
                "name": "premium"
            },
            "properties": {
                "managedResourceGroupId": "[concat('/subscriptions/', subscription().subscriptionId, '/resourceGroups/databricks-rg-', parameters('workspaceName'), '-', uniqueString(parameters('workspaceName'), resourceGroup().id))]",
                "parameters": {
                    "enableNoPublicIp": {
                        "value": False
                    },
                    "prepareEncryption": {
                        "value": False
                    },
                    "customVirtualNetworkId": {
                        "value": "[resourceId('Microsoft.Network/virtualNetworks', parameters('vnetName'))]"
                    },
                    "customPublicSubnetName": {
                        "value": "[parameters('publicSubnetName')]"
                    },
                    "customPrivateSubnetName": {
                        "value": "[parameters('privateSubnetName')]"
                    }
                }
            },
            "dependsOn": [
                "[resourceId('Microsoft.Network/virtualNetworks', parameters('vnetName'))]"
            ]
        }
    ],
    "outputs": {
        "workspaceResourceId": {
            "type": "string",
            "value": "[resourceId('Microsoft.Databricks/workspaces', parameters('workspaceName'))]"
        }
    }
}

# ------------------------
# Parameters for template
# ------------------------
parameters = {
    "workspaceName": {"value": WORKSPACE_NAME},
    "location": {"value": LOCATION},
    "vnetName": {"value": VNET_NAME},
    "vnetPrefix": {"value": VNET_PREFIX},
    "publicSubnetName": {"value": PUBLIC_SUBNET_NAME},
    "publicSubnetPrefix": {"value": PUBLIC_SUBNET_PREFIX},
    "privateSubnetName": {"value": PRIVATE_SUBNET_NAME},
    "privateSubnetPrefix": {"value": PRIVATE_SUBNET_PREFIX},
}


# ------------------------
# Helper functions
# ------------------------
def cleanup_failed_deployment():
    """Clean up resources if deployment fails"""
    print("Cleaning up failed deployment resources...")
    cred = DefaultAzureCredential()
    resource_client = ResourceManagementClient(credential=cred, subscription_id=SUBSCRIPTION_ID)

    try:
        # Delete the deployment
        resource_client.deployments.begin_delete(RESOURCE_GROUP, DEPLOYMENT_NAME).wait()
        print(f"Deleted deployment: {DEPLOYMENT_NAME}")
    except Exception as e:
        print(f"Could not delete deployment: {e}")

# ------------------------
# Authenticate and deploy
# ------------------------
def main():
    print("Authenticating with DefaultAzureCredential...")
    cred = DefaultAzureCredential()
    resource_client = ResourceManagementClient(credential=cred, subscription_id=SUBSCRIPTION_ID)

    # Ensure resource group exists for the deployment
    print(f"Ensuring resource group '{RESOURCE_GROUP}' exists in {LOCATION}...")
    rg_result = resource_client.resource_groups.create_or_update(RESOURCE_GROUP, {"location": LOCATION})
    print("Resource group ready:", rg_result.name)

    # Start deployment
    print(f"Starting ARM deployment '{DEPLOYMENT_NAME}'...")
    deployment = Deployment(
        properties={
            "mode": DeploymentMode.incremental,
            "template": arm_template,
            "parameters": parameters
        }
    )

    deployment_poller = resource_client.deployments.begin_create_or_update(
        RESOURCE_GROUP,
        DEPLOYMENT_NAME,
        deployment
    )

    print("Deployment in progress... this may take 10-20 minutes depending on region and resources.")
    try:
        deployment_result = deployment_poller.result()
        print("Deployment finished. Provisioning state:", deployment_result.properties.provisioning_state)
    except Exception as e:
        print(f"Deployment failed: {e}")
        print("Checking deployment operations for more details...")
        try:
            ops = resource_client.deployment_operations.list(RESOURCE_GROUP, DEPLOYMENT_NAME)
            for op in ops:
                if hasattr(op.properties, 'statusMessage') and op.properties.statusMessage:
                    print(f"Operation {op.properties.target_resource.resource_name if op.properties.target_resource else 'unknown'}: {op.properties.status_message}")
        except Exception as op_error:
            print(f"Could not retrieve deployment operations: {op_error}")
        raise

    outputs = deployment_result.properties.outputs or {}
    workspace_id = outputs.get("workspaceResourceId", {}).get("value")
    print("Workspace resourceId:", workspace_id)
    return workspace_id


if __name__ == "__main__":
    try:
        wid = main()
        print(f"\n[SUCCESS] Deployment completed successfully!")
        print(f"Workspace ID: {wid}")
    except Exception as e:
        print(f"\n[ERROR] Deployment failed: {str(e)}")
        print("\nTo clean up failed resources, you can run:")
        print("python -c \"from deploy_databricks_workspace import cleanup_failed_deployment; cleanup_failed_deployment()\"")
        raise
