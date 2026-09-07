pipeline {
    agent any

    environment {
    AWS_REGION = 'us-east-1'
    ECR_REPOSITORY = '127372371582.dkr.ecr.us-east-1.amazonaws.com/rag-chatbot'
    IMAGE_TAG = "build-${BUILD_NUMBER}"
}

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    ./venv/bin/pip install --upgrade pip
                    ./venv/bin/pip install -r requirements.txt
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    ./venv/bin/python -m pytest -v
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    docker build -t ${ECR_REPOSITORY}:${IMAGE_TAG} .
                '''
            }
        }
        stage('ECR Login') {
            steps {
                sh '''
                    aws ecr get-login-password --region ${AWS_REGION} | \
                    docker login --username AWS --password-stdin ${ECR_REPOSITORY}
                '''
            }
        }
         stage('Docker Push') {
            steps {
                sh '''
                    docker push ${ECR_REPOSITORY}:${IMAGE_TAG}
                '''
            }
        }
    }
}