# Kubernetes deployment

Create the namespace and runtime secret outside Git, then apply the base manifests:

```sh
kubectl create secret generic skillsync-secrets -n skillsync \
  --from-literal=SESSION_SECRET="$SESSION_SECRET" \
  --from-literal=DATABASE_URL="$DATABASE_URL" \
  --from-literal=FIREBASE_SERVICE_ACCOUNT_KEY="$FIREBASE_SERVICE_ACCOUNT_KEY"
kubectl apply -k infrastructure/kubernetes/base
```

The deployment uses the versioned `skillsync/core-service:0.1.0` image. Update that tag in the deployment during CI/CD promotion; do not use `latest`.
