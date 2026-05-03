#!/bin/bash
# =============================================================================
# deploy.sh — Build & déploiement de la Lambda Pegasus sur AWS
# Prérequis : AWS CLI configuré, Docker installé
# Usage     : bash deploy.sh
# =============================================================================

set -e

# ── Variables à adapter ────────────────────────────────────────────────────────
AWS_REGION="eu-west-3"           # Paris
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO_NAME="pegasus-lambda"
FUNCTION_NAME="pegasus-inscription"
IMAGE_TAG="latest"
ROLE_NAME="pegasus-lambda-role"
# ──────────────────────────────────────────────────────────────────────────────

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}"

echo "=== [1/6] Création du repo ECR (si inexistant)..."
aws ecr describe-repositories --repository-names "${REPO_NAME}" --region "${AWS_REGION}" 2>/dev/null || \
  aws ecr create-repository --repository-name "${REPO_NAME}" --region "${AWS_REGION}"

echo "=== [2/6] Login Docker vers ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | \
  docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "=== [3/6] Build de l'image Docker..."
docker build --platform linux/amd64 -t "${REPO_NAME}:${IMAGE_TAG}" .

echo "=== [4/6] Tag & Push vers ECR..."
docker tag "${REPO_NAME}:${IMAGE_TAG}" "${ECR_URI}:${IMAGE_TAG}"
docker push "${ECR_URI}:${IMAGE_TAG}"

echo "=== [5/6] Création / mise à jour de la fonction Lambda..."

# Vérifie si la fonction existe déjà
if aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${AWS_REGION}" 2>/dev/null; then
  echo "  Mise à jour du code existant..."
  aws lambda update-function-code \
    --function-name "${FUNCTION_NAME}" \
    --image-uri "${ECR_URI}:${IMAGE_TAG}" \
    --region "${AWS_REGION}"
else
  echo "  Création du rôle IAM..."
  TRUST_POLICY='{
    "Version":"2012-10-17",
    "Statement":[{
      "Effect":"Allow",
      "Principal":{"Service":"lambda.amazonaws.com"},
      "Action":"sts:AssumeRole"
    }]
  }'
  ROLE_ARN=$(aws iam create-role \
    --role-name "${ROLE_NAME}" \
    --assume-role-policy-document "${TRUST_POLICY}" \
    --query "Role.Arn" --output text 2>/dev/null || \
    aws iam get-role --role-name "${ROLE_NAME}" --query "Role.Arn" --output text)

  aws iam attach-role-policy \
    --role-name "${ROLE_NAME}" \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" 2>/dev/null || true

  echo "  Attente de la propagation du rôle IAM (10s)..."
  sleep 10

  echo "  Création de la fonction Lambda..."
  aws lambda create-function \
    --function-name "${FUNCTION_NAME}" \
    --package-type Image \
    --code "ImageUri=${ECR_URI}:${IMAGE_TAG}" \
    --role "${ROLE_ARN}" \
    --timeout 120 \
    --memory-size 1024 \
    --region "${AWS_REGION}"
fi

echo "=== [6/6] Injection des variables d'environnement (credentials)..."
# Les credentials sont passés en env vars, jamais dans le code
aws lambda update-function-configuration \
  --function-name "${FUNCTION_NAME}" \
  --environment "Variables={PEGASUS_USERNAME=vincent.esperance@alumni.chimie-paristech.fr,PEGASUS_PASSWORD=V.Esp6991}" \
  --timeout 120 \
  --memory-size 1024 \
  --region "${AWS_REGION}"

echo ""
echo "✅ Déploiement terminé !"
echo "   Fonction : ${FUNCTION_NAME}"
echo "   Image    : ${ECR_URI}:${IMAGE_TAG}"
echo ""
echo "Pour tester manuellement :"
echo "  aws lambda invoke --function-name ${FUNCTION_NAME} --region ${AWS_REGION} output.json && cat output.json"
