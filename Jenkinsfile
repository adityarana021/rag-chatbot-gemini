pipeline {
    agent any

    environment {
        AWS_REGION = 'us-east-1'
        ECR_REGISTRY = '127372371582.dkr.ecr.us-east-1.amazonaws.com'
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
                    docker login --username AWS --password-stdin ${ECR_REGISTRY}
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

        stage('Clone GitOps Repo') {
            steps {
                dir('gitops') {
                    git(
                        credentialsId: 'github-pat',
                        url: 'https://github.com/adityarana021/rag-chatbot-gitops.git',
                        branch: 'main'
                    )
                }
            }
        }

        stage('Update Image Tag') {
            steps {
                dir('gitops') {
                    sh """
                        sed -i 's|image: .*|image: ${ECR_REPOSITORY}:${IMAGE_TAG}|' app/deployment.yaml

                        echo "Updated deployment:"
                        grep 'image:' app/deployment.yaml
                    """
                }
            }
        }

        stage('Push GitOps Changes') {
            steps {
                dir('gitops') {
                    withCredentials([usernamePassword(
                        credentialsId: 'github-pat',
                        usernameVariable: 'GITHUB_USER',
                        passwordVariable: 'GITHUB_TOKEN'
                    )]) {
                        sh '''
                            git config user.name "Jenkins"
                            git config user.email "jenkins@localhost"

                            git add app/deployment.yaml
                            git commit -m "Update image to build-${BUILD_NUMBER}" || true

                            git push https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/adityarana021/rag-chatbot-gitops.git main
                        '''
                    }
                }
            }
        }
    }
}