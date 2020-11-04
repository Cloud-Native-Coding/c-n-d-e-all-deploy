# Manifest for c-n-d-e Controller

## Installation

1. Setup a new Cluster at running Dashboard instance. Note values for API Key and Cluster Name
2. Edit <TENANT>/kustomization.yaml

change literals for config map `saas-controller-config` for `CNDE_API_KEY` and `CNDE_CLUSTER_NAME`

3. Deploy c-n-d-e Controller

```bash
kubectl create ns <TENANT> # create namespace
kustomize build ./<TENANT> | kubectl apply -f - # deploy
```

## cleanup

1. Execute

```bash
kustomize build ./<TENANT> | kubectl delete -f -
kubectl delete ns <TENANT>
make clean # removes folder so be sure !!!
```
