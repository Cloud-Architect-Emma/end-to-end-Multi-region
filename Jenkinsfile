pipeline {
  agent {
    docker {
      image 'emmanuelacode/devops-ci:latest'
      args '-v /var/run/docker.sock:/var/run/docker.sock'
    }
  }

  environment {
    AWS_DEFAULT_REGION  = "us-east-1"
    AWS_SECOND_REGION   = "us-east-2"
    SERVICE_NAME        = "cartservice"
    IMAGE_TAG           = ""
  }

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
    timeout(time: 60, unit: 'MINUTES')
  }

  parameters {
    string(name: 'BRANCH_NAME', defaultValue: 'main', description: 'Branch to build')
    booleanParam(name: 'DEPLOY_TO_K8S', defaultValue: false, description: 'Deploy to Kubernetes cluster?')
  }

  stages {

    stage('Checkout') {
      steps {
        checkout([
          $class: 'GitSCM',
          branches: [[name: "*/${params.BRANCH_NAME}"]],
          userRemoteConfigs: [[url: 'https://github.com/Cloud-Architect-Emma/end-to-end-Multi-region.git']]
        ])
        script {
          env.GIT_COMMIT_SHORT = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
        }
      }
    }

    stage('Pre-commit & Format') {
      steps {
        sh '''
          if command -v pre-commit >/dev/null 2>&1; then
            pre-commit run --all-files || true
          else
            echo "pre-commit not installed, skipping"
          fi
        '''
      }
    }

    stage('Install Dev Dependencies') {
      steps {
        sh '''
          if [ -f package.json ]; then npm ci; fi
          if [ -f requirements.txt ]; then python -m pip install -r requirements.txt --user; fi
        '''
      }
    }

    stage('Lint') {
      steps {
        sh '''
          if [ -f package.json ]; then npm run lint || true; fi
          if [ -f requirements.txt ]; then flake8 || true; fi
        '''
      }
    }

    stage('Unit Tests & Coverage') {
      steps {
        sh '''
          if [ -f package.json ]; then npm test --if-present || true; fi
          if [ -f requirements.txt ]; then pytest --maxfail=1 --disable-warnings -q || true; fi
        '''
      }
    }

    stage('Build Docker Image') {
      steps {
        script {
          env.IMAGE_TAG = "${params.BRANCH_NAME}-${env.BUILD_NUMBER}-${env.GIT_COMMIT_SHORT}"
        }
        sh '''
          echo "IMAGE_TAG=$IMAGE_TAG" > .image_tag

          # Build the service image (corrected path)
          docker build -t $SERVICE_NAME:$IMAGE_TAG \
            multi-region-project/microservices-demo/src/cartservice/
        '''
      }
    }

    stage('Generate SBOM (Syft)') {
      steps {
        sh '''
          IMAGE_TAG=$(cut -d'=' -f2 .image_tag)
          if command -v syft >/dev/null 2>&1; then
            syft $SERVICE_NAME:$IMAGE_TAG -o json > .sbom.json || true
          else
            echo "Syft not installed; skipping SBOM"
          fi
        '''
      }
    }

    stage('Trivy Vulnerability Scan') {
      steps {
        sh '''
          IMAGE_TAG=$(cut -d'=' -f2 .image_tag)
          if command -v trivy >/dev/null 2>&1; then
            trivy image --exit-code 1 --severity CRITICAL,HIGH $SERVICE_NAME:$IMAGE_TAG || true
          else
            echo "Trivy not installed; skipping scan"
          fi
        '''
      }
    }

    stage('Push to ECR Multi-Region') {
      steps {
        withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-creds']]) {
          script {
            env.AWS_ACCOUNT_ID = sh(script: "aws sts get-caller-identity --query Account --output text", returnStdout: true).trim()
            env.ECR_PRIMARY    = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/${SERVICE_NAME}"
            env.ECR_SECONDARY  = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_SECOND_REGION}.amazonaws.com/${SERVICE_NAME}"
          }
          sh '''
            IMAGE_TAG=$(cut -d'=' -f2 .image_tag)

            # Create ECR repositories if missing
            aws ecr describe-repositories --region $AWS_DEFAULT_REGION --repository-names $SERVICE_NAME >/dev/null 2>&1 || \
              aws ecr create-repository --region $AWS_DEFAULT_REGION --repository-name $SERVICE_NAME

            aws ecr describe-repositories --region $AWS_SECOND_REGION --repository-names $SERVICE_NAME >/dev/null 2>&1 || \
              aws ecr create-repository --region $AWS_SECOND_REGION --repository-name $SERVICE_NAME

            # Login to both ECR regions
            aws ecr get-login-password --region $AWS_DEFAULT_REGION | \
              docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com

            aws ecr get-login-password --region $AWS_SECOND_REGION | \
              docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_SECOND_REGION}.amazonaws.com

            # Tag the image for each region
            docker tag $SERVICE_NAME:$IMAGE_TAG $ECR_PRIMARY:$IMAGE_TAG
            docker tag $SERVICE_NAME:$IMAGE_TAG $ECR_SECONDARY:$IMAGE_TAG

            # Push to both regions
            docker push $ECR_PRIMARY:$IMAGE_TAG
            docker push $ECR_SECONDARY:$IMAGE_TAG
          '''
        }
      }
    }

    stage('Observability & Predictive Scaling') {
      when { expression { params.DEPLOY_TO_K8S } }
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
          sh '''
            export KUBECONFIG=$KUBECONFIG_FILE

            # Deploy Prometheus + Grafana manifests if present
            if [ -d monitoring ]; then
              kubectl apply -f monitoring/
            else
              echo "No monitoring/ manifests found; skipping"
            fi

            # CPU-based predictive scaling
            CPU=$(kubectl top pod $SERVICE_NAME --no-headers 2>/dev/null | awk '{print $2}' | sed 's/%//')
            if [ -n "$CPU" ] && [ "$CPU" -gt 80 ]; then
              echo "CPU usage high ($CPU%), scaling up..."
              kubectl scale deployment $SERVICE_NAME --replicas=3 || true
            else
              echo "CPU metric unavailable or below threshold; no scaling"
            fi
          '''
        }
      }
    }

    stage('Archive artifacts') {
      steps {
        archiveArtifacts artifacts: '.image_tag, .sbom.json', allowEmptyArchive: true
      }
    }
  }

  post {
    success { echo "Pipeline completed successfully ✅" }
    failure { echo "Pipeline failed ❌" }
  }
}
