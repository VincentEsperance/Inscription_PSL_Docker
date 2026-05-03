# Pegasus Lambda — Auto-inscription Volley PSL

Fonction Lambda Docker qui se connecte automatiquement au portail Pegasus PSL
et inscrit l'utilisateur au **Volley 3 du lundi** de la semaine suivante.

## Structure

```
pegasus-lambda/
├── handler.py        # Logique Playwright (automation)
├── Dockerfile        # Image Lambda avec Chromium
├── requirements.txt  # Dépendances Python
├── deploy.sh         # Script de build + déploiement AWS
└── README.md
```

## Prérequis

- Docker installé et en cours d'exécution
- AWS CLI configuré (`aws configure`)
- Droits IAM : ECR, Lambda, IAM

## Déploiement

```bash
chmod +x deploy.sh
bash deploy.sh
```

Le script :
1. Crée un repo ECR `pegasus-lambda`
2. Build l'image Docker (linux/amd64)
3. Push vers ECR
4. Crée ou met à jour la Lambda `pegasus-inscription`
5. Configure les variables d'environnement (credentials)

## Test manuel

```bash
aws lambda invoke \
  --function-name pegasus-inscription \
  --region eu-west-3 \
  output.json && cat output.json
```

## Planification avec EventBridge

Pour déclencher automatiquement chaque lundi (ex: 7h00 heure de Paris = 6h00 UTC en été) :

1. AWS Console → EventBridge → Rules → Create rule
2. **Schedule expression** : `cron(0 6 ? * MON *)`
3. **Target** : Lambda → `pegasus-inscription`

⚠️ Les inscriptions ouvrent à une heure précise sur Pegasus. Adapter le cron en conséquence.

## Réponse de la Lambda

```json
{
  "success": true,
  "message": "Inscription prise en compte !",
  "logs": [
    "[07:00:01] Lancement de Chromium (headless)...",
    "[07:00:03] Navigation vers https://...",
    "[07:00:05] Connexion reussie.",
    "[07:00:07] Page calendrier chargee.",
    "[07:00:09] Semaine suivante affichee.",
    "[07:00:11] Creneau trouve.",
    "[07:00:13] Inscription prise en compte !"
  ]
}
```

## Sécurité

Les credentials sont stockés en **variables d'environnement Lambda**.
Pour plus de sécurité, les migrer vers **AWS Secrets Manager** :

```python
import boto3, json
client = boto3.client("secretsmanager", region_name="eu-west-3")
secret = json.loads(client.get_secret_value(SecretId="pegasus/credentials")["SecretString"])
USERNAME = secret["username"]
PASSWORD = secret["password"]
```

## Note sur Python 3.14

Python 3.14 n'est pas encore disponible en image Lambda officielle AWS.
L'image utilise Python **3.12** (dernière version disponible), au comportement identique pour ce cas d'usage.
Mettre à jour le `FROM` dans le Dockerfile dès que AWS publie l'image 3.14.
