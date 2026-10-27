/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

# tfdoc:file:description Factories: allowed endpoints (Agent Gateway access policies) and PSC Interface network attachments.

locals {
  # Variables available in every factory YAML file as ${name} (rendered with templatefile)
  factory_vars = {
    organization_id = var.organization_id
    project_id      = var.project_id
    project_number  = var.project_number
    region          = var.region
  }

  _endpoints_path = try(pathexpand(var.factories_config.endpoints), null)
  _raw_factory_files = {
    for f in try(fileset(local._endpoints_path, "**/*.yaml"), []) :
    trimsuffix(basename(f), ".yaml") => yamldecode(templatefile(
      "${local._endpoints_path}/${f}", local.factory_vars
    ))
  }

  # Each YAML file contains named blocks mapping specific principal(s) to their own allowed host(s).
  # Each block becomes an isolated IAM v3 UAP rule so Principal A can only reach Block A's hosts
  # and Principal B can only reach Block B's hosts.
  _factory_endpoints = merge([
    for file_key, file_val in local._raw_factory_files : {
      for block_key, block_val in file_val :
      "${file_key}-${block_key}" => block_val
    }
  ]...)

  _factory_endpoint_conditions = {
    for k, v in local._factory_endpoints : k => compact([
      lookup(v, "host", null) != null
      ? "destination.unregistered.host == '${v.host}'"
      : null,
      length(lookup(v, "hosts", [])) > 0
      ? "destination.unregistered.host in [${join(", ", [for h in v.hosts : "'${h}'"])}]"
      : null,
      lookup(v, "path_prefix", null) != null
      ? "destination.unregistered.path.startsWith('${v.path_prefix}')"
      : null,
      lookup(v, "method", null) != null
      ? "destination.unregistered.method == '${v.method}'"
      : null,
      length(lookup(v, "methods", [])) > 0
      ? "destination.unregistered.method in [${join(", ", [for m in v.methods : "'${m}'"])}]"
      : null,
      lookup(v, "condition", null)
    ])
  }

  factory_endpoint_rules = {
    for k, v in local._factory_endpoints : k => {
      description = lookup(v, "description", null)
      effect      = lookup(v, "effect", "ALLOW")
      principals = compact(concat(
        lookup(v, "principal", null) != null ? [v.principal] : [],
        lookup(v, "principals", [])
      ))
      excluded_principals = lookup(v, "excluded_principals", [])
      permissions = lookup(
        v, "permissions", ["iap.googleapis.com/resources.egressViaIAP"]
      )
      excluded_permissions = lookup(v, "excluded_permissions", [])
      registry             = lookup(v, "registry", false)
      agent_id             = lookup(v, "agent_id", null)
      endpoint_id          = lookup(v, "endpoint_id", null)
      mcp_server_id        = lookup(v, "mcp_server_id", null)
      location             = lookup(v, "location", null)
      condition_service    = lookup(v, "condition_service", "iap.googleapis.com")
      condition = (
        length(local._factory_endpoint_conditions[k]) > 0
        ? join(" && ", local._factory_endpoint_conditions[k])
        : (
          lookup(v, "registry", false)
          || lookup(v, "agent_id", null) != null
          || lookup(v, "endpoint_id", null) != null
          || lookup(v, "mcp_server_id", null) != null
          ? null
          : "destination.is_registered == false"
        )
      )
    }
  }
}

# ---------------------------------------------------------------------------
# PSC Interface network attachments factory (data/network-attachments/*.yaml)
# ---------------------------------------------------------------------------

locals {
  _network_attachments_path = try(pathexpand(var.factories_config.network_attachments), null)
  _network_attachments_files = {
    for f in try(fileset(local._network_attachments_path, "**/*.yaml"), []) :
    f => yamldecode(templatefile("${local._network_attachments_path}/${f}", local.factory_vars))
  }

  # Each top-level YAML key is one network attachment (key = attachment name)
  factory_network_attachments = merge([
    for f, v in local._network_attachments_files : {
      for name, a in v : name => {
        subnet_self_link      = a.subnet_self_link
        automatic_connection  = lookup(a, "automatic_connection", true)
        description           = lookup(a, "description", null)
        producer_accept_lists = lookup(a, "producer_accept_lists", null)
        producer_reject_lists = lookup(a, "producer_reject_lists", null)
      }
    } if v != null
  ]...)
}

