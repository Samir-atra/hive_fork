---
description: How to configure and use MongoDB credentials in Hive
---
# MongoDB Credentials Integration in Hive

This workflow explains how to set up, configure, and manage credentials for MongoDB within the Hive framework using `aden_tools.credentials`.

## Overview

The MongoDB credential specification provides a standardized way for agents to access a MongoDB database (e.g., MongoDB Atlas or a local instance) using standard connection string URIs. Health checking is built-in and validates the credentials by connecting and issuing a simple database `ping`. 

## Prerequisites
- A MongoDB instance running locally or on MongoDB Atlas.
- `pymongo` installed in your project (`poetry add pymongo` or `pip install pymongo`).

## Step 1: Acquiring a MongoDB URI

To obtain a connection string:
1. Log in to your MongoDB database hosting provider (e.g., [MongoDB Atlas](https://cloud.mongodb.com/)).
2. Create or navigate to a Cluster.
3. Access **Database Access** and add a new database user.
4. Access **Network Access** and ensure your IP address is allowed.
5. In your cluster view, click **Connect** -> **Drivers**, and choose Python.
6. Copy the connection string provided (it usually starts with `mongodb+srv://` or `mongodb://`). Replace `<username>` and `<password>` with your actual credentials.

## Step 2: Configuring Credentials

You can use the `hive-credentials` workflow or `.env` files.

### Option A: Using the `hive-credentials` Skill (Recommended)

1. Use `/hive-credentials` from your agent interface or CLI tool to detect missing credentials.
2. The agent will prompt for the `MONGODB_URI` environment variable if your agent requires tools such as `mongodb_insert_document`.
3. Provide the full connection string URI. The credential will be securely stored and encrypted in `~/.hive/credentials`.

### Option B: Using `.env` overrides

If you prefer environment variables for development:
```bash
export MONGODB_URI="mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority"
```

## Step 3: MongoDB Tools

Agents requiring MongoDB memory storage can utilize the built-in standard tools for MongoDB (which map to the `MONGODB_URI`). 
- `mongodb_insert_document`
- `mongodb_find_documents`
- `mongodb_update_document`
- `mongodb_list_collections`
- `mongodb_aggregate`

Make sure your agent configuration assigns these tools appropriately so that it triggers the credential check.

## Step 4: Troubleshooting

- **Dependency Error:** If the health check returns "pymongo not installed," please run `poetry add pymongo` or `pip install pymongo`.
- **Connection Issues:** Health checks proactively execute an `admin.command("ping")` against the configured URI. If it fails, double-check your username, password, and Network Access configuration (IP Whitelist) on Atlas.
