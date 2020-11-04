#!/usr/bin/python3

import subprocess
import getpass
import json
import argparse
import os
import shutil
import secrets

parser = argparse.ArgumentParser(
    description='Create Kubernetes Manifests for c-n-d-e Dashboard, c-n-d-e Operator and c-n-d-e Controller')

parser.add_argument('-tenant', required=True, help='name of the Dashboard and API tenant')
parser.add_argument('-keycloak', required=True,
                    help='Keycloak hostname (e.g. keycloak)')
parser.add_argument('-cluster_domain', required=True,
                    help='Domain of IDE-Cluster(e.g kubeplatform.dev)')
parser.add_argument('-dashboard_domain', required=False,
                    help='Domain of Dashboard and API (e.g kubeplatform.dev)')
parser.add_argument('-pw', required=True,
                    help='initial password for oauth-users')

args = parser.parse_args()
REALM = args.tenant  # args.realm
CLUSTER_DOMAIN = args.cluster_domain
DASHBOARD_DOMAIN = args.dashboard_domain
TENANT = args.tenant
KEYCLOAK = args.keycloak
PW = args.pw

if args.dashboard_domain is None:
    DASHBOARD_DOMAIN = CLUSTER_DOMAIN
    print(f"Using Cluster Domain \"{CLUSTER_DOMAIN}\" as Dashboard Domain")

KEYCLOAK_HOST = f"{KEYCLOAK}.{CLUSTER_DOMAIN}"

password = getpass.getpass("Whats your Keycloak Admin Password? ")

oauthSecret = secrets.token_urlsafe(16)

class Keycloak:
    KC = "bin/kcadm.sh "

    def __init__(self, keycloakPW, keycloakHost, tenant, realm, dashboardDomain, initialPW):
        self.keycloakHost = keycloakHost
        self.tenant = tenant
        self.realm = realm
        self.keycloakPW = keycloakPW
        self.dashboardDomain = dashboardDomain
        self.initialPW = initialPW
        self.secret = None

    def __escapeJson(object):
        return "'" + json.dumps(object) + "'"

    def __kc(self, script):
        return subprocess.run(Keycloak.KC + script, check=True, shell=True, stdout=subprocess.PIPE).stdout.decode('utf-8').strip()

    def __getClientSecret(self, cid):
        return json.loads(
            self.__kc(f"get clients/{cid}/client-secret -r {self.realm}"))["value"]

    def __getClient(self):
        return json.loads(
            self.__kc(f"get clients?clientId=c-n-d-e -r {self.realm}"))[0]["id"]

    def provision(self):
        self.__kc(
            f"config credentials --server https://{self.keycloakHost}/auth --realm master --user keycloak --password {self.keycloakPW}")

        print(f"Keycloak: get or create Realm \"{TENANT}\"")
        try:
            self.__kc(
                f"create realms -s realm={self.tenant} -s enabled=true -o")
        except:
            print(
                f"\nRealm \"{self.tenant}\" already exists. Reusing it... Remove it if appropriate...")
            self.secret = self.__getClientSecret(self.__getClient())
            return

        print(f"Keycloak: get or create Client")
        try:
            CID = self.__getClient()
        except:
            CID = self.__kc(f"create clients -r {self.realm}" +
                            """ -s clientId=c-n-d-e -s 'redirectUris=["*"]' -s rootUrl=https://""" + f"cnde.{self.tenant}.{self.dashboardDomain} -s adminUrl=cnde.{self.tenant}.{self.dashboardDomain} -i")

        self.secret = self.__getClientSecret(CID)

        print("Keycloak: create User")
        self.__kc(
            f"create users -s username=cnde -s enabled=true -s emailVerified=true -s email=cnde@cnde.{self.tenant}.{self.dashboardDomain} -r {self.tenant}")
        self.__kc(
            f"set-password -r {self.tenant} --username cnde --new-password {self.initialPW} --temporary")


class Openssl:
    CERT_DAYS = 1095

    def __init__(self, targetPath):
        self.targetPath = targetPath

    def __openssl(self, script):
        return subprocess.run(f"openssl {script}", check=True, shell=True)

    def createCerts(self):
        try:
            os.makedirs(self.targetPath, exist_ok=False)
        except:
            print("cert files seem to exist. Skipping creation...")
            return
        # Generate the CA Key and Certificate:
        self.__openssl(
            f"req -x509 -sha256 -newkey rsa:4096 -keyout {self.targetPath}/ca.key -out {self.targetPath}/ca.crt -days {self.CERT_DAYS} -nodes -subj '/CN=Cloud Native Coding'")
        # Generate the Server Key, and Certificate and Sign with the CA Certificate:
        self.__openssl(
            f"req -new -newkey rsa:4096 -keyout {self.targetPath}/server.key -out {self.targetPath}/server.csr -nodes -subj '/CN=*.{TENANT}.{DASHBOARD_DOMAIN}'")
        self.__openssl(
            f"x509 -req -sha256 -days {self.CERT_DAYS} -in {self.targetPath}/server.csr -CA {self.targetPath}/ca.crt -CAkey {self.targetPath}/ca.key -set_serial 01 -out {self.targetPath}/server.crt")
        # Generate the Client Key, and Certificate and Sign with the CA Certificate:
        self.__openssl(
            f"req -new -newkey rsa:4096 -keyout {self.targetPath}/client.key -out {self.targetPath}/client.csr -nodes -subj '/CN=*.{TENANT}.{DASHBOARD_DOMAIN}'")
        self.__openssl(
            f"x509 -req -sha256 -days {self.CERT_DAYS} -in {self.targetPath}/client.csr -CA {self.targetPath}/ca.crt -CAkey {self.targetPath}/ca.key -set_serial 02 -out {self.targetPath}/client.crt")

#############################
# Creating Realm in Keycloak
#############################


kc = Keycloak(password, KEYCLOAK_HOST, TENANT, REALM, DASHBOARD_DOMAIN, PW)
kc.provision()
oauthClientSecret = kc.secret

#############################
# Creating directories
#############################

targetPath = f"./generated/{TENANT}"
try:
    os.makedirs(targetPath, exist_ok=True)
    shutil.copytree(f"./c-n-d-e-operator",
                    f"{targetPath}/c-n-d-e-operator", dirs_exist_ok=True)
    shutil.copytree(f"./c-n-d-e-dashboard",
                    f"{targetPath}/c-n-d-e-dashboard", dirs_exist_ok=True)
    shutil.copytree(f"./c-n-d-e-controller",
                    f"{targetPath}/c-n-d-e-controller", dirs_exist_ok=True)
except OSError:
    print(f"Creation of the directories in {targetPath} failed")

#############################
# Creating stuff for Operator
#############################

with open(f"{targetPath}/c-n-d-e-operator/kustomization.yaml", "w") as text_file:
    print(f"""bases:
- ./base
#
patchesStrategicMerge:
- manager_patch.yaml
#
secretGenerator:
- name: cnde-oauth
  behavior: replace
  literals:
    - CNDE_OAUTH_ADMIN_NAME=keycloak
    - CNDE_OAUTH_ADMIN_PASSWORD={password}
    - CNDE_OAUTH_ADMIN_REALM={TENANT}
    - CNDE_OAUTH_INITIAL_PW={PW}
    - CNDE_OAUTH_URL=https://{KEYCLOAK_HOST}
  type: Opaque
#
generatorOptions:
  disableNameSuffixHash: true
#
namespace: c-n-d-e-system""", file=text_file)

##############################
# Creating stuff for Dashboard
##############################

# create and store certificates
ssl = Openssl(f"{targetPath}/c-n-d-e-dashboard/certs")
ssl.createCerts()

with open(f"{targetPath}/c-n-d-e-dashboard/kustomization.yaml", "w") as text_file:
    print(f"""bases:
  - ./base
#
secretGenerator:
  - name: api-ca-secret
    files:
      - certs/ca.crt
  - name: cnde-web-oauth-proxy
    behavior: replace
    literals:
      - client_id=c-n-d-e
      - client_secret={oauthClientSecret}
      - cookie_secret={oauthSecret}
#
configMapGenerator:
  - name: cnde-config
    behavior: replace
    literals:
      - DOMAIN={DASHBOARD_DOMAIN}
#
generatorOptions:
  disableNameSuffixHash: true""", file=text_file)

###############################
# Creating stuff for Controller
###############################

clientCertDir = f"{targetPath}/c-n-d-e-controller/api-client-certs"
os.makedirs(f"{clientCertDir}", exist_ok=True)
shutil.copyfile(f"{targetPath}/c-n-d-e-dashboard/certs/client.crt",
                f"{clientCertDir}/client.pem")
shutil.copyfile(f"{targetPath}/c-n-d-e-dashboard/certs/client.key",
                f"{clientCertDir}/client.key")

with open(f"{targetPath}/c-n-d-e-controller/kustomization.yaml", "w") as text_file:
    print(f"""resources:
  - ./base

configMapGenerator:
  - name: saas-controller-config
    literals:
      - CNDE_API_KEY=... # INSERT YOUR API KEY HERE (create one in running Dashboard)
      - CNDE_CLUSTER_NAME=.. # INSERT YOUR CLUSTER NAME HERE (create one in running Dashboard)
      - CNDE_URL=https://api.{DASHBOARD_DOMAIN}
      - CNDE_KEYCLOAK_HOST={KEYCLOAK}

secretGenerator:
  - name: api-client-cert
    files:
      - ./api-client-certs/client.pem
      - ./api-client-certs/client.key

generatorOptions:
  disableNameSuffixHash: true

namespace: c-n-d-e-system""", file=text_file)

################################

print(f"\n*******\nDone. Created files at {targetPath}")
print("Please also refer to the respective README.md")
