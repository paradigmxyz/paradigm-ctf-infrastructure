import base64
import http.client
import pickle
import time

from ctf_server.databases.database import Database
from ctf_server.types import (
    AnvilInstanceMetadata,
    InstanceInfo,
    LaunchAnvilInstanceArgs,
)
from kubernetes.client.api import core_v1_api
from kubernetes.client.exceptions import ApiException
from kubernetes.client.models import V1Pod

from kubernetes import config

from .backend import Backend


class KubernetesBackend(Backend):
    def __init__(self, database: Database, kubeconfig: str) -> None:
        super().__init__(database)

        if kubeconfig == "incluster":
            config.load_incluster_config()
        else:
            config.load_kube_config(kubeconfig)

        self.__core_v1 = core_v1_api.CoreV1Api()

    def launch_anvil_instance_impl(
        self, instance_id: str, args: LaunchAnvilInstanceArgs
    ) -> AnvilInstanceMetadata:
        pod_manifest = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": f"anvil-{instance_id}"},
            "spec": {
                "containers": [
                    {
                        "image": args.image,
                        "name": f"container",
                        "command": ["anvil"],
                        "args": args.format_args(port="8545"),
                        "ports": [
                            {
                                "containerPort": 8545,
                            },
                        ],
                    },
                ],
            },
        }

        api_response: V1Pod = self.__core_v1.create_namespaced_pod(
            namespace="default", body=pod_manifest
        )

        while True:
            api_response = self.__core_v1.read_namespaced_pod(
                name=pod_manifest["metadata"]["name"], namespace="default"
            )
            if api_response.status.phase != "Pending":
                break
            time.sleep(1)

        return {
            "backend_id": f"anvil-{instance_id}",
            "ip": api_response.status.pod_ip,
            "port": 8545,
        }

    def kill_instance(self, instance_id: str) -> InstanceInfo:
        instance = self._database.unregister_instance(instance_id)
        if instance is None:
            return None

        self.__core_v1.delete_namespaced_pod(
            namespace="default", name=f"anvil-{instance_id}"
        )

        while True:
            try:
                self.__core_v1.read_namespaced_pod(
                    namespace="default",
                    name=f"anvil-{instance_id}",
                )
            except ApiException as e:
                if e.status == http.client.NOT_FOUND:
                    break

            time.sleep(0.5)

        return instance
