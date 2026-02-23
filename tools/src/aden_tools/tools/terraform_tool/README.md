# Terraform Tool

Infrastructure as Code automation for Aden agents, enabling programmatic management of cloud infrastructure via the Terraform CLI.

## Description

This tool provides structured, agent-friendly wrappers around the [Terraform CLI](https://developer.hashicorp.com/terraform). It enables DevOps agents to initialise working directories, generate execution plans, apply or destroy infrastructure, manage workspaces, and read state — all through the MCP protocol.

Terraform must be installed on the host system and available on `PATH`.

## Tools

### Core Lifecycle

| Tool | Description |
|------|-------------|
| `terraform_init` | Initialise a Terraform working directory (downloads providers, configures backend) |
| `terraform_validate` | Validate configuration files for syntax and internal consistency |
| `terraform_plan` | Generate an execution plan showing proposed changes |
| `terraform_apply` | Apply changes to create or update infrastructure |
| `terraform_destroy` | Destroy Terraform-managed infrastructure |

### State & Output Inspection

| Tool | Description |
|------|-------------|
| `terraform_show` | Display current state in structured JSON |
| `terraform_output` | Read output values from the state |
| `terraform_read_state` | Read state and return a resource summary |

### Workspace Management

| Tool | Description |
|------|-------------|
| `terraform_workspace_list` | List available workspaces and identify the current one |
| `terraform_workspace_select` | Switch to a different workspace |

### Configuration Management

| Tool | Description |
|------|-------------|
| `terraform_write_config` | Write `.tf` or `.tfvars` configuration files |
| `terraform_import_resource` | Import existing infrastructure into Terraform state |

## Arguments

### `terraform_init`

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `working_dir` | str | Yes | — | Path to Terraform working directory |
| `backend_config` | str | No | `""` | Comma-separated key=value backend config overrides |
| `upgrade` | bool | No | `False` | Upgrade modules and plugins |
| `reconfigure` | bool | No | `False` | Reconfigure backend ignoring saved config |

### `terraform_plan`

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `working_dir` | str | Yes | — | Path to Terraform working directory |
| `variables` | str | No | `""` | Comma-separated key=value variable overrides |
| `var_file` | str | No | `""` | Path to `.tfvars` file |
| `target` | str | No | `""` | Resource address to target |
| `destroy` | bool | No | `False` | Plan a destroy operation |

### `terraform_apply` / `terraform_destroy`

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `working_dir` | str | Yes | — | Path to Terraform working directory |
| `variables` | str | No | `""` | Comma-separated key=value variable overrides |
| `var_file` | str | No | `""` | Path to `.tfvars` file |
| `target` | str | No | `""` | Resource address to target |
| `auto_approve` | bool | No | `False` | Skip interactive approval (**use with caution**) |

### `terraform_write_config`

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `working_dir` | str | Yes | — | Path to Terraform working directory |
| `filename` | str | Yes | — | File name (must end with `.tf` or `.tfvars`) |
| `config_content` | str | Yes | — | HCL or variable content to write |

### `terraform_import_resource`

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `working_dir` | str | Yes | — | Path to Terraform working directory |
| `address` | str | Yes | — | Terraform resource address (e.g. `aws_instance.web`) |
| `resource_id` | str | Yes | — | Provider-specific resource ID |

## Environment Variables

This tool does **not** require any API keys or secrets of its own. Terraform providers use standard cloud credentials (e.g. `AWS_ACCESS_KEY_ID`, `GOOGLE_CREDENTIALS`, `ARM_CLIENT_ID`). These should be set independently in the host environment.

## Prerequisites

- **Terraform CLI** ≥ 1.0 on `PATH` — [Install guide](https://developer.hashicorp.com/terraform/install)

## Security Considerations

- **Destructive operations** (`apply`, `destroy`) default to `auto_approve=False` — an explicit opt-in is required.
- **State files** may contain sensitive data; use remote state backends with encryption in production.
- **`write_config`** restricts filenames to `.tf` / `.tfvars` and prevents path traversal.
- Commands run with `TF_IN_AUTOMATION=1` and `TF_INPUT=0` to prevent interactive prompts.

## Error Handling

All tools return `{"error": "..."}` on failure instead of raising exceptions. Common errors:

- `Working directory does not exist` — invalid `working_dir` path
- `Terraform CLI not found on PATH` — Terraform is not installed
- `Terraform command timed out` — operation exceeded the timeout limit

## Example Workflow

```
1. Agent generates Terraform HCL → terraform_write_config(dir, "main.tf", hcl)
2. Agent initialises → terraform_init(dir)
3. Agent validates → terraform_validate(dir)
4. Agent previews changes → terraform_plan(dir, variables="region=us-east-1")
5. Agent applies → terraform_apply(dir, variables="region=us-east-1", auto_approve=True)
6. Agent reads outputs → terraform_output(dir)
7. When done → terraform_destroy(dir, auto_approve=True)
```
