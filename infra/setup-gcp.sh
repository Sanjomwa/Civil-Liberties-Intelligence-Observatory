#!/bin/bash
# setup-gcp.sh - Kenya Civil Liberties & Censorship Observatory GCP Setup

set -e

# === CONFIG ===
PROJECT_ID="encoded-joy-485413-k5"
SERVICE_ACCOUNT_NAME="terraform-sa"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="terraform-key.json"
REGION="us-central1"

echo "🚀 Setting up GCP for Kenya Civil Liberties & Censorship Observatory"
echo "Project ID : $PROJECT_ID"
echo "Region     : $REGION"

# Set the project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "Enabling GCP APIs..."
gcloud services enable \
    storage.googleapis.com \
    bigquery.googleapis.com \
    iam.googleapis.com \
    cloudresourcemanager.googleapis.com

# Create service account
echo "Creating Terraform service account..."
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --project=$PROJECT_ID \
    --display-name="Terraform Service Account" || echo "Service account already exists"

# Assign roles
echo "Assigning roles..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/bigquery.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/iam.serviceAccountUser"

# Generate key file
echo "Generating new service account key..."
gcloud iam service-accounts keys create $KEY_FILE \
    --iam-account=$SERVICE_ACCOUNT_EMAIL \
    --project=$PROJECT_ID

echo ""
echo "✅ Setup complete!"
echo "Key file created: $KEY_FILE"
echo ""
echo "Next steps:"
echo "1. export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/$KEY_FILE"
echo "2. cd infra"
echo "3. terraform init"
echo "4. terraform plan"
echo "5. terraform apply"