# Companyz namespace
resource "kubernetes_namespace" "companyz_namespace" {
  metadata {
    name = var.companyz_namespace
  }
}

# Companyz tx-connector
module "companyz_tx-connector" {
  source = "./modules/tx-connector"

  humanReadableName = var.companyz_humanReadableName
  namespace         = kubernetes_namespace.companyz_namespace.metadata[0].name
  participantId     = var.companyz_bpn

  dcp_config = {
    id                     = "did:web:companyz.${local.domain_name}"
    sts_token_url          = "https://companyz.${local.domain_name}/api/sts/token"
    sts_client_id          = "did:web:companyz.${local.domain_name}"
    sts_clientsecret_alias = "did:web:companyz.${local.domain_name}-sts-client-secret"
    issuer                 = "did:web:issuer.${local.domain_name}"
  }

  dataplane = {
    privatekey_alias = "did:web:companyz.${local.domain_name}#signing-key-1"
    publickey_alias  = "did:web:companyz.${local.domain_name}#signing-key-1"
  }

  connector_hostname = "companyz.${local.domain_name}"
  bdrs_hostname      = "bdrs.${local.domain_name}"
}

# Companyz tx-identity-hub
module "companyz_tx-identity-hub" {
  depends_on = [module.companyz_tx-connector]

  source = "./modules/tx-identity-hub"

  humanReadableName   = var.companyz_humanReadableName
  namespace           = kubernetes_namespace.companyz_namespace.metadata[0].name
  participantId       = var.companyz_bpn
  vault-url           = local.companyz_vault-url
  ih_superuser_apikey = var.companyz_ih_superuser_apikey

  aliases = {
    sts-private-key   = "did:web:issuer.${local.domain_name}#signing-key-1"
    sts-public-key-id = "did:web:issuer.${local.domain_name}#signing-key-1"
  }

  datasource = {
    username = var.companyz_datasource.username
    password = var.companyz_datasource.password
    url      = local.companyz_jdbcUrl
  }

  image = var.tx-identity-hub_image
}

# Companyz ingress for tx-connector and tx-identity-hub
module "companyz_connector_ingress" {
  depends_on = [module.companyz_tx-identity-hub]

  source = "./modules/tx-connector-ingress"

  humanReadableName = var.companyz_humanReadableName
  namespace         = kubernetes_namespace.companyz_namespace.metadata[0].name
  domain_name       = local.domain_name

}

locals {
  companyz_vault-url = "http://${lower(var.companyz_humanReadableName)}-vault:8200"
  companyz_jdbcUrl   = "jdbc:postgresql://${lower(var.companyz_humanReadableName)}-postgresql:${var.companyz_datasource.database_port}/${var.companyz_datasource.database_name}"
}