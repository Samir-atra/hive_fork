# Docker Management Tool

Manage Docker containers, images, and system stats directly through Hive agents.

## Requirements

- **Docker Engine**: Must be installed and running on the host system.
- **Permissions**: The user running the Hive agent must have permissions to access the Docker socket (e.g., be in the `docker` group on Linux).

## Tools

### Container Management
- `docker_list_containers`: List all containers (running or all).
- `docker_container_action`: Start, stop, restart, or kill specific containers.
- `docker_get_logs`: Retrieve stdout/stderr logs from a container.
- `docker_remove_container`: Delete containers and associated volumes.

### Image Management
- `docker_list_images`: List locally available images.
- `docker_pull_image`: Pull images from Docker Hub or private registries.
- `docker_remove_image`: Remove unused images.

### System & Inspection
- `docker_get_stats`: Get real-time resource usage (CPU, Memory, IO).
- `docker_inspect`: Get detailed low-level information about a container or image.

## Implementation Details
This tool uses the `docker-py` library. It connects to the Docker daemon using the default environment configuration (`docker.from_env()`).
