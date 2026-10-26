locals {
  # Merge factory-loaded endpoint rules (data/endpoints/*.yaml) with any inline var.endpoint_rules
  gateway_egress_rules = merge(local.factory_endpoint_rules, var.endpoint_rules)
}

# ---------------------------------------------------------------------------
# GEAP Agent Gateway (Egress: AGENT_TO_ANYWHERE)
# Routes both PUBLIC and PRIVATE endpoints via Agent Connectivity Template
# ---------------------------------------------------------------------------

module "agent_gateway" {
  # Using local Cloud Foundation Fabric checkout (or switch to GitHub source below):
  # source = "github.com/GoogleCloudPlatform/cloud-foundation-fabric//modules/geap-agent-gateway?ref=master"
  source = "/usr/local/google/home/dibaskar/cloud-foundation-fabric/modules/geap-agent-gateway"

  name           = var.gateway_name
  project_id     = var.project_id
  project_number = var.project_number
  region         = var.region
  access_path    = "AGENT_TO_ANYWHERE"
  registries     = var.registries

  networking_config = {
    psc_i_network_attachment_id = var.psc_i_network_attachment_id
    access_types                = var.access_types # ["PUBLIC", "PRIVATE"]
    vpc_egress                  = var.vpc_egress
    dns_peering_config          = var.dns_peering_config
  }

  iap_config = {
    iam_enforcement_mode = var.iap_enforcement_mode
    policy_version       = "V2"
  }

  access_policies = length(local.gateway_egress_rules) > 0 ? {
    "${var.gateway_name}-egress-policy" = {
      display_name    = "Agent Gateway Egress Access Policy"
      target_resource = "project"
      rules           = local.gateway_egress_rules
    }
  } : {}
}
