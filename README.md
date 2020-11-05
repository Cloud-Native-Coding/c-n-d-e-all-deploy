# Cloud Native Coding IDEs

This Script creates kustomize/Kubernetes manifests to deploy the following 3 components:

1. **Dashboard / API**: Consists of a Management UI and an API
1. **c-n-d-e Controller**: Queries the API and creates CRs for the c-n-d-e Operator
1. **c-n-d-e Operator**: Reacts to CRs (like DevEnv) and operates IDEs

The usual 2 cluster setup is as follows:

* Cluster 1 (**Dashboard cluster**) contains:
  + a Keycloak instance for Dashboard authentication
  + a WEB-Dashboard instance
  + a API for c-n-d-e Controller instances
* Cluster 2 (**IDE cluster**) contains:
  + a Keycloak instance for IDE authentication
  + c-n-d-e Controller calling the API
  + c-n-d-e Operator creating and deleting IDEs on Cluster 2

However, all components can be installed on the same cluster.
If it also makes sense to have more than one dashboard instance, this can be done by using more than one tenant.

## Creating Manifests

prerequisites:

* Python 3.x
* a clone of this repo

The CLI `cnde.py` creates kustomize manifest in folder `generated`

The arguments:

```bash
./cnde.py -h
usage: cnde.py [-h] -tenant TENANT -keycloak KEYCLOAK -cluster_domain CLUSTER_DOMAIN [-dashboard_domain DASHBOARD_DOMAIN] -pw PW

Create Kubernetes Manifests for c-n-d-e Dashboard, c-n-d-e Operator and c-n-d-e Controller

optional arguments:
  -h, --help            show this help message and exit
  -tenant TENANT        name of the Dashboard and API tenant
  -keycloak KEYCLOAK    Keycloak hostname (e.g. keycloak)
  -cluster_domain CLUSTER_DOMAIN
                        Domain of IDE-Cluster(e.g kubeplatform.dev)
  -dashboard_domain DASHBOARD_DOMAIN
                        Domain of Dashboard and API (e.g kubeplatform.dev)
  -pw PW                initial password for oauth-users
```

### Example

 `./cnde.py -tenant mytenant -keycloak keycloak -cluster_domain kubeplatform.dev -dashboard_domain dashboard.dev -pw 0815`

This will:

* create a **Realm** `mytenant` in a Keycloak instance at `keycloak.dashboard.dev`
* create **API certs** for mTLS for Domain `dashboard.dev`
* create the **manifests** in folder `generated/mytenant`

Scripts should be reviewed and can be applied to the respective cluster afterwards.
