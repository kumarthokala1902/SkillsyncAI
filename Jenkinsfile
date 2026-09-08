pipeline {
    agent any

    environment {
        IMAGE_NAME = "skillsync"
        IMAGE_TAG = "${BUILD_NUMBER}"
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Pulling code from GitHub...'
                checkout scm
            }
        }

        stage('Docker Build') {
            steps {
                echo 'Building Docker image...'

                sh '''
                    docker build \
                    -t ${IMAGE_NAME}:${IMAGE_TAG} \
                    -t ${IMAGE_NAME}:latest \
                    .
                '''
            }
        }

        stage('Verify Image') {
            steps {
                sh '''
                    docker images | grep ${IMAGE_NAME}
                '''
            }
        }
    }

    post {

        success {
            echo "Docker image successfully built: ${IMAGE_NAME}:${IMAGE_TAG}"
        }

        failure {
            echo 'Pipeline failed. Check the Jenkins console output.'
        }
    }
}
