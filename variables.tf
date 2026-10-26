variable "project_id" {
  description = "The ID of the Google Cloud project where the Agent Gateway will be deployed."
  type        = string
}

variable "project_number" {
  description = "Optional project number of var.project_id. Providing this avoids an extra google_project data source lookup when building the connectivity template reference."
  type        = string
  default     = null
}

variable "region" {
  description = "The Google Cloud region where the Agent Gateway is created."
  type        = string
  default     = "us-east4"
}

# ---------------------------------------------------------------------------
# Agent Gateway variables
# ---------------------------------------------------------------------------

variable "gateway_name" {
  description = "The name of the egress Agent Gateway."
  type        = string
  default     = "agent-egress-gw"
}

variable "psc_i_network_attachment_id" {
  description = "Full resource ID of the PSC Interface network attachment used by the Agent Gateway connectivity template to reach private VPC endpoints (e.g., projects/<host-project>/regions/<region>/networkAttachments/<name>)."
  type        = string
}

variable "access_types" {
  description = "Endpoint access types routed through the Agent Gateway connectivity template. Include both PUBLIC and PRIVATE to route both public and private endpoints."
  type        = list(string)
  default     = ["PUBLIC", "PRIVATE"]
}

variable "vpc_egress" {
  description = "VPC egress mode on the connectivity template: 'ALL_TRAFFIC' (all public and private traffic routed through the VPC attachment) or 'PRIVATE_RANGES_ONLY' (private IPs via VPC attachment, public IPs via Google egress)."
  type        = string
  default     = "ALL_TRAFFIC"
}

variable "dns_peering_config" {
  description = "Optional DNS peering configuration for resolving private domains in the target VPC network through the Agent Gateway connectivity template."
  type = object({
    domains        = list(string)
    target_network = string
  })
  default = null
}

variable "registries" {
  description = "Optional list of Agent Registries governed by the Agent Gateway (format: //agentregistry.googleapis.com/projects/<project>/locations/<location>)."
  type        = list(string)
  default     = null
}

variable "factories_config" {
  description = "Paths to data folders that enable Cloud Foundation Fabric factory functionality for allowed endpoints."
  type = object({
    endpoints = optional(string, "./data/endpoints")
  })
  nullable = false
  default  = {}
}

variable "endpoint_rules" {
  description = "Additional inline allowed endpoint rules merged with YAML factory endpoint rules."
  type = map(object({
    principals           = list(string)
    agent_id             = optional(string)
    condition            = optional(string)
    condition_service    = optional(string, "iap.googleapis.com")
    description          = optional(string)
    effect               = optional(string, "ALLOW")
    endpoint_id          = optional(string)
    excluded_permissions = optional(list(string), [])
    excluded_principals  = optional(list(string), [])
    location             = optional(string)
    mcp_server_id        = optional(string)
    permissions = optional(
      list(string), ["iap.googleapis.com/resources.egressViaIAP"]
    )
    registry = optional(bool, false)
  }))
  nullable = false
  default  = {}
}

variable "iap_enforcement_mode" {
  description = "IAP enforcement mode for the Agent Gateway. Leave null to enforce IAM Unified Access Policies, or set to 'DRY_RUN' for audit-only mode."
  type        = string
  default     = null
}
