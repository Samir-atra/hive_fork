"""
MongoDB credentials for NoSQL Database Integration.

Contains connection string credentials for MongoDB (Atlas or Local).
"""

from .base import CredentialSpec

MONGODB_CREDENTIALS = {
    "mongodb": CredentialSpec(
        env_var="MONGODB_URI",
        tools=[
            "mongodb_insert_document",
            "mongodb_find_documents",
            "mongodb_update_document",
            "mongodb_list_collections",
            "mongodb_aggregate",
        ],
        required=False,
        startup_required=False,
        help_url="https://cloud.mongodb.com/",
        description="Connection credentials for MongoDB (Atlas or Local) via standard URI.",
        # Auth method support
        aden_supported=False,
        direct_api_key_supported=True,
        api_key_instructions="""To get a MongoDB Connection String:

1. Log in to MongoDB Atlas (https://cloud.mongodb.com/).
2. Create a Cluster (Free Tier available).
3. Go to Database Access -> Create a Database User (User/Password).
4. Go to Network Access -> Allow IP Address (0.0.0.0/0 for dev, or specific IP).
5. Click Connect -> Drivers -> Python.
6. Copy the Connection String (e.g., mongodb+srv://<username>:<password>@cluster0.mongodb.net/).""",
        # Credential store mapping
        credential_id="mongodb",
        credential_key="connection_string",
    ),
}
