# Manifest for c-n-d-e Dashboard

## Installation

```bash
kubectl create ns <TENANT> # create namespace
kustomize build ./<TENANT> | kubectl apply -f - # deploy
```

## cleanup

Execute:

```bash
kustomize build ./<TENANT> | kubectl delete -f -
kubectl delete ns <TENANT>
make clean # removes folder so be sure !!!
```
