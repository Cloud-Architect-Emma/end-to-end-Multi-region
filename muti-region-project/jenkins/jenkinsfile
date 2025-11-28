
pipeline {
    agent any

    environment {
        AWS_DEFAULT_REGION = "eu-west-1"
        AWS_SECOND_REGION  = "us-east-1"
        ECR_ACCOUNT_ID     = "YOUR_AWS_ACCOUNT_ID"
        SERVICE_NAME       = "cartservice"

        // ECR Repositories (multi-region)
        ECR_REPO_PRIMARY   = "${ECR_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/${SERVICE_NAME}"
        ECR_REPO_SECONDARY = "${ECR_ACCOUNT_ID}.dkr.ecr.${AWS_SECOND_REGION}.amazonaws.com/${SERVICE_NAME}"
    }

    options {
        timestamps()
        skipStagesAfterUnstable()
    }

    stages {

        /* ------------------------------------------ */
        /* 1) CHECKOUT CODE                           */
        /* ------------------------------------------ */
        stage('Checkout Code') {
            steps {
                git branch: "${env.BRANCH_NAME}", url: 'https://github.com/Cloud-Architect-Emma/end-to-end-Multi-region.git'
            }
        }   


        /* ------------------------------------------ */
        /* 2) INSTALL DEV DEPENDENCIES (Lint/Test)     */
        /* ------------------------------------------ */
        stage('Install Dev Dependencies') {
            steps {
                script {

                    if (fileExists('package.json')) {
                        sh '''
                          echo "Node project detected — installing dev dependencies"
                          npm ci
                        '''
                    }

                    if (fileExists('requirements-dev.txt')) {
                        sh '''
                          echo "Python project detected — installing dev dependencies"
                          pip install -r requirements-dev.txt
                        '''
                    }
                }
            }
        }


        /* ------------------------------------------ */
        /* 3) LINTING                                  */
        /* ------------------------------------------ */
        stage('Lint Code') {
            steps {
                script {

                    if (fileExists('package.json')) {
                        sh 'npm run lint || true'     // do not fail pipeline for linting
                    }

                    if (fileExists('requirements-dev.txt')) {
                        sh 'flake8 || true'
                    }

                }
            }
        }


        /* ------------------------------------------ */
        /* 4) RUN TESTS                                */
        /* ------------------------------------------ */
        stage('Run Tests') {
            steps {
                script {

                    if (fileExists('package.json')) {
                        sh 'npm test'
                    }

                    if (fileExists('requirements-dev.txt')) {
                        sh 'pytest'
                    }

                }
            }
        }


        /* ------------------------------------------ */
        /* 5) BUILD DOCKER IMAGE (runtime deps)        */
        /* ------------------------------------------ */
        stage('Build Docker Image') {
            steps {
                script {
                    sh '''
                      IMAGE_TAG=${BRANCH_NAME}-${BUILD_NUMBER}

                      echo "IMAGE_TAG=$IMAGE_TAG" > .image_tag
                      
                      docker build -t ${SERVICE_NAME}:$IMAGE_TAG .
                    '''
                }
            }
        }


        /* ------------------------------------------ */
        /* 6) AUTH TO AWS ECR + PUSH                   */
        /* ------------------------------------------ */
        stage('Push to ECR (Multi-Region)') {
            steps {
                script {
                    IMAGE_TAG = readFile('.image_tag').trim()

                    sh """
                      echo "Authenticating to ECR..."
                      aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REPO_PRIMARY
                      aws ecr get-login-password --region $AWS_SECOND_REGION | docker login --username AWS --password-stdin $ECR_REPO_SECONDARY

                      echo "Tagging for primary region..."
                      docker tag ${SERVICE_NAME}:$IMAGE_TAG $ECR_REPO_PRIMARY:$IMAGE_TAG

                      echo "Tagging for secondary region..."
                      docker tag ${SERVICE_NAME}:$IMAGE_TAG $ECR_REPO_SECONDARY:$IMAGE_TAG

                      echo "Pushing to ECR primary..."
                      docker push $ECR_REPO_PRIMARY:$IMAGE_TAG

                      echo "Pushing to ECR secondary..."
                      docker push $ECR_REPO_SECONDARY:$IMAGE_TAG
                    """
                }
            }
        }

        /* ------------------------------------------ */
        /* 7) OPTIONAL — AUTO-DEPLOY STAGING           */
        /* ------------------------------------------ */
        stage('Deploy to Staging (optional)') {
            when {
                branch 'staging'
            }
            steps {
                sh '''
                  echo "Deploying to staging Kubernetes/ECS..."
                  # kubectl apply -f k8s/staging.yaml
                '''
            }
        }

    }

    /* ------------------------------------------ */
    /* 8) POST-BUILD ACTIONS                       */
    /* ------------------------------------------ */
    post {
        success {
            echo "CI Pipeline Completed Successfully! ✔"
        }
        failure {
            echo "Pipeline Failed ❌ – Check console logs"
        }
    }
}
