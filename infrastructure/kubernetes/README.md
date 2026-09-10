# Kubernetes deployment

The base manifests deploy the Docker Hub image as `skillsync-core` on port 5000
and expose it through the `skillsync.com` Ingress host. The standalone
`pod.yaml` is provided for one-pod troubleshooting; normal deployments use the
Deployment and should not apply both at the same time.

The runtime Secret is created by Jenkins from its credentials. For a manual
deployment, create it without committing the values:

```sh
kubectl create secret generic skillsync-secrets -n skillsync \
  --from-literal=SESSION_SECRET="$SESSION_SECRET" \
  --from-file=FIREBASE_SERVICE_ACCOUNT_KEY="$FIREBASE_SERVICE_ACCOUNT_KEY"
kubectl apply -k infrastructure/kubernetes/base
```

The Jenkins pipeline uses the `dockerhub_credentials` username/password
credential to build, push, and pull an immutable image tag. After the approval
stage, it applies the base and updates the Deployment to that verified tag.
The pipeline also expects a Jenkins file credential named `kubeconfig`.

Configure the GitHub repository webhook to notify the Jenkins job on push so
the `githubPush()` trigger starts the pipeline after each commit.
