output "network_attachment_ids" {
  description = "IDs of the PSC Interface network attachments created from the factory, keyed by name."
  value       = module.network_attachments.network_attachment_ids
}

output "agent_gateway_id" {
  description = "The fully qualified ID of the egress Agent Gateway (pass to geap-agent-runtime networking_config.agent_gateways.egress)."
  value       = module.agent_gateway.id
}

output "agent_gateway_connectivity_template_id" {
  description = "The ID of the Agent Connectivity Template attached to the Agent Gateway."
  value       = module.agent_gateway.connectivity_template_id
}

output "agent_gateway_access_policy_ids" {
  description = "The IAM v3 Unified Access Policy IDs bound to the Agent Gateway."
  value       = module.agent_gateway.access_policy_ids
}

output "agent_gateway_policy_binding_ids" {
  description = "The IAM v3 policy binding IDs, keyed by policy key."
  value       = module.agent_gateway.policy_binding_ids
}

output "agent_gateway_authz_extension_ids" {
  description = "The authorization extension IDs, keyed by service."
  value       = module.agent_gateway.authz_extension_ids
}

output "agent_gateway_authz_policy_ids" {
  description = "The authorization policy IDs, keyed by service."
  value       = module.agent_gateway.authz_policy_ids
}
