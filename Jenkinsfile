pipeline {
    agent any

    triggers {
        githubPush()
    }

    parameters {
        string(
            name: 'DOCKERHUB_REPOSITORY',
            defaultValue: 'skillsync/core-service',
            description: 'Docker Hub repository, including the Docker Hub namespace'
        )
    }

    environment {
        KUBERNETES_NAMESPACE = 'skillsync'
        KUBECONFIG_CREDENTIALS_ID = 'kubeconfig'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build, Push, and Verify Image') {
            steps {
                script {
                    def commit = sh(
                        script: 'git rev-parse --short=7 HEAD',
                        returnStdout: true
                    ).trim()
                    env.IMAGE_TAG = "${env.BUILD_NUMBER}-${commit}"
                    env.IMAGE = "${params.DOCKERHUB_REPOSITORY}:${env.IMAGE_TAG}"
                }

                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub_credentials',
                        usernameVariable: 'DOCKER_USERNAME',
                        passwordVariable: 'DOCKER_PASSWORD'
                    )
                ]) {
                    sh '''
                        set -eu
                        echo "$DOCKER_PASSWORD" | docker login \
                            -u "$DOCKER_USERNAME" \
                            --password-stdin
                        docker build --pull -t "$IMAGE" .
                        docker push "$IMAGE"
                        docker pull "$IMAGE"
                        docker image inspect "$IMAGE" >/dev/null
                        docker logout >/dev/null 2>&1 || true
                    '''
                }
            }
        }

        stage('Approve Kubernetes Deployment') {
            steps {
                timeout(time: 2, unit: 'MINUTES') {
                    input message: 'Do you need to deploy into the Kubernetes? If yes continue the deployment else stop the pipeline.', ok: 'Deploy'
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                withCredentials([
                    file(
                        credentialsId: env.KUBECONFIG_CREDENTIALS_ID,
                        variable: 'KUBECONFIG'
                    ),
                    usernamePassword(
                        credentialsId: 'dockerhub_credentials',
                        usernameVariable: 'DOCKER_USERNAME',
                        passwordVariable: 'DOCKER_PASSWORD'
                    ),
                    string(
                        credentialsId: 'skillsync_session_secret',
                        variable: 'SESSION_SECRET'
                    ),
                    file(
                        credentialsId: 'skillsync_firebase_service_account',
                        variable: 'FIREBASE_SERVICE_ACCOUNT_KEY'
                    )
                ]) {
                    sh '''
                        set -eu
                        kubectl create namespace "$KUBERNETES_NAMESPACE" \
                            --dry-run=client -o yaml | kubectl apply -f -

                        kubectl create secret docker-registry dockerhub-registry \
                            --namespace "$KUBERNETES_NAMESPACE" \
                            --docker-server=https://index.docker.io/v1/ \
                            --docker-username="$DOCKER_USERNAME" \
                            --docker-password="$DOCKER_PASSWORD" \
                            --dry-run=client -o yaml | kubectl apply -f -

                        kubectl create secret generic skillsync-secrets \
                            --namespace "$KUBERNETES_NAMESPACE" \
                            --from-literal=SESSION_SECRET="$SESSION_SECRET" \
                            --from-file=FIREBASE_SERVICE_ACCOUNT_KEY="$FIREBASE_SERVICE_ACCOUNT_KEY" \
                            --dry-run=client -o yaml | kubectl apply -f -

                        kubectl apply -k infrastructure/kubernetes/base
                        kubectl -n "$KUBERNETES_NAMESPACE" set image \
                            deployment/skillsync-core core-service="$IMAGE"
                        kubectl -n "$KUBERNETES_NAMESPACE" rollout status \
                            deployment/skillsync-core --timeout=5m
                    '''
                }
            }
        }
    }

    post {
        always {
            sh 'docker logout >/dev/null 2>&1 || true'
        }
    }
}
