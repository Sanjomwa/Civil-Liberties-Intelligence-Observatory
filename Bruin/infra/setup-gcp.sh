#!/bin/bash

# Exit immediately if a command fails
set -e

# === CONFIG ===
PROJECT_ID="civil-liberties-prod"
SERVICE_ACCOUNT_NAME="terraform-sa"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="terraform-key.json"
REGION="us-central1"

echo "Setting up GCP project: $PROJECT_ID"

# 1. Enable required APIs
echo "Enabling required GCP APIs..."
gcloud services enable compute.googleapis.com \
    storage.googleapis.com \
    bigquery.googleapis.com \
    iam.googleapis.com

# 2. Create service account
echo "Creating Terraform service account..."
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --project=$PROJECT_ID \
    --display-name="Terraform Service Account"

# 3. Assign roles
echo "Assigning roles to service account..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/editor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/bigquery.admin"

# 4. Generate key file
echo "Generating service account key..."
gcloud iam service-accounts keys create $KEY_FILE \
    --iam-account=$SERVICE_ACCOUNT_EMAIL \
    --project=$PROJECT_ID

echo "✅ Setup complete. Key file saved as $KEY_FILE"
echo "Next steps:"
echo "1. Export GOOGLE_APPLICATION_CREDENTIALS:"
echo "   export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/$KEY_FILE"
echo "2. Run 'terraform init' in infra/"
echo "3. Run 'terraform plan' to preview changes"
echo "4. Run 'terraform apply' to deploy infrastructure"
