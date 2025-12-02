pipeline {
  agent any

  environment {
    AWS_DEFAULT_REGION  = "us-east-1"
    AWS_SECOND_REGION   = "us-east-2"
    SERVICE_NAME        = "cartservice"
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

    stage('Checkout SCM') {
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

    stage('Tooling Check') {
      steps {
        sh '''
          which docker || { echo "docker not found"; exit 1; }
          docker version || { echo "docker daemon not reachable"; exit 1; }
          which aws    || echo "aws CLI not found (will fail on ECR steps)"
          which kubectl|| echo "kubectl not found (K8s deploy disabled unless present)"
          which syft   || echo "syft not found (SBOM will be skipped)"
          which trivy  || echo "trivy not found (scan will be skipped)"
        '''
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
          SHORT_SHA = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
          IMAGE_TAG = "${params.BRANCH_NAME}-${BUILD_NUMBER}-${SHORT_SHA}"

          sh """
            echo "IMAGE_TAG=$IMAGE_TAG" > .image_tag
            echo "Building image: $SERVICE_NAME:$IMAGE_TAG"

            docker build -t "$SERVICE_NAME:$IMAGE_TAG" \
              -f muti-region-project/microservices-demo/src/cartservice/Dockerfile \
              muti-region-project/microservices-demo/src/cartservice/
          """
        }
      }
    }

    stage('Update Trivy DB') {
      steps {
        sh '''
          if command -v trivy >/dev/null 2>&1; then
            trivy image --refresh alpine:3.19 || true
          else
            echo "Trivy not installed; skipping DB update"
          fi
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
            trivy image --scanners vuln --exit-code 1 --severity CRITICAL,HIGH $SERVICE_NAME:$IMAGE_TAG || true
          else
            echo "Trivy not installed; skipping scan"
          fi
        '''
      }
    }

    stage('Push to ECR Multi-Region') {
      steps {
        withCredentials([
          string(credentialsId: 'aws-access-key-id', variable: 'AWS_ACCESS_KEY_ID'),
          string(credentialsId: 'aws-secret-access-key', variable: 'AWS_SECRET_ACCESS_KEY')
        ]) {
          script {
            env.AWS_ACCOUNT_ID = sh(script: "aws sts get-caller-identity --query Account --output text", returnStdout: true).trim()
            env.ECR_PRIMARY    = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/${SERVICE_NAME}"
            env.ECR_SECONDARY  = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_SECOND_REGION}.amazonaws.com/${SERVICE_NAME}"
          }
          sh '''
            IMAGE_TAG=$(cut -d'=' -f2 .image_tag)

            # Ensure repos exist
            aws ecr describe-repositories --repository-names $SERVICE_NAME --region $AWS_DEFAULT_REGION || \
              aws ecr create-repository --repository-name $SERVICE_NAME --region $AWS_DEFAULT_REGION

            aws ecr describe-repositories --repository-names $SERVICE_NAME --region $AWS_SECOND_REGION || \
              aws ecr create-repository --repository-name $SERVICE_NAME --region $AWS_SECOND_REGION

            # Login and push
            aws ecr get-login-password --region $AWS_DEFAULT_REGION | \
              docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com

            aws ecr get-login-password --region $AWS_SECOND_REGION | \
              docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_SECOND_REGION}.amazonaws.com

            docker tag $SERVICE_NAME:$IMAGE_TAG $ECR_PRIMARY:$IMAGE_TAG
            docker tag $SERVICE_NAME:$IMAGE_TAG $ECR_SECONDARY:$IMAGE_TAG
            docker push $ECR_PRIMARY:$IMAGE_TAG
            docker push $ECR_SECONDARY:$IMAGE_TAG
          '''
        }
      }
    }





stage('Deploy to EKS') {
  when { expression { params.DEPLOY_TO_K8S } }
  steps {
    withCredentials([
      string(credentialsId: 'aws-access-key-id', variable: 'AWS_ACCESS_KEY_ID'),
      string(credentialsId: 'aws-secret-access-key', variable: 'AWS_SECRET_ACCESS_KEY')
    ]) {
      sh '''
        IMAGE_TAG=$(cut -d'=' -f2 .image_tag)

        # Configure kubeconfig for your EKS cluster in us-east-1
        aws eks update-kubeconfig --region us-east-1 --name multi-region

        echo "Deploying $SERVICE_NAME:$IMAGE_TAG to EKS cluster 'multi-region' in us-east-1..."

        # Update deployment image
        kubectl set image deployment/$SERVICE_NAME \
          $SERVICE_NAME=${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/$SERVICE_NAME:$IMAGE_TAG \
          --record

        # Wait for rollout to complete
        kubectl rollout status deployment/$SERVICE_NAME --timeout=180s
      '''
    }
  }
}


stage('Monitoring ServiceAccounts') {
  steps {
    withCredentials([
      file(credentialsId: 'kubeconfig.yaml', variable: 'KUBECONFIG_FILE'),
      string(credentialsId: 'aws-access-key-id', variable: 'AWS_ACCESS_KEY_ID'),
      string(credentialsId: 'aws-secret-access-key', variable: 'AWS_SECRET_ACCESS_KEY')
    ]) {
      sh '''
        export KUBECONFIG=$KUBECONFIG_FILE
        export AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
        export AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
        export AWS_DEFAULT_REGION=us-east-1

        aws sts get-caller-identity   # sanity check
        kubectl apply -f manifests/monitoring/serviceaccounts.yaml
      '''
    }
  }
}

stage('Monitoring RBAC') {
  steps {
    withCredentials([
      file(credentialsId: 'kubeconfig.yaml', variable: 'KUBECONFIG_FILE'),
      string(credentialsId: 'aws-access-key-id', variable: 'AWS_ACCESS_KEY_ID'),
      string(credentialsId: 'aws-secret-access-key', variable: 'AWS_SECRET_ACCESS_KEY')
    ]) {
      sh '''
        export KUBECONFIG=$KUBECONFIG_FILE
        export AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
        export AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
        export AWS_DEFAULT_REGION=us-east-1

        kubectl apply -f manifests/monitoring/rbac.yaml
      '''
    }
  }
}

stage('Monitoring Datasource') {
  steps {
    withCredentials([
      file(credentialsId: 'kubeconfig.yaml', variable: 'KUBECONFIG_FILE'),
      string(credentialsId: 'aws-access-key-id', variable: 'AWS_ACCESS_KEY_ID'),
      string(credentialsId: 'aws-secret-access-key', variable: 'AWS_SECRET_ACCESS_KEY')
    ]) {
      sh '''
        export KUBECONFIG=$KUBECONFIG_FILE
        export AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
        export AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
        export AWS_DEFAULT_REGION=us-east-1

        kubectl apply -f manifests/monitoring/grafana-datasource.yaml
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

            if [ -d monitoring ]; then
              kubectl apply -f monitoring/
            else
              echo "No monitoring/ manifests found; skipping"
            fi

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

    stage('Cleanup Docker Images') {
      steps {
        sh '''
          echo "Cleaning up old Docker images..."
          docker image prune -f
          LATEST=$(docker images --format "{{.Repository}}:{{.Tag}}" \
            | grep "^cartservice:main-" \
            | sort -r \
            | head -n1)
          docker images --format "{{.Repository}}:{{.Tag}}" \
            | grep "^cartservice:main-" \
            | grep -v "$LATEST" \
            | xargs -r docker rmi || true
          echo "Cleanup complete. Latest image preserved: $LATEST"
        '''
      }
    }
  }

  post {
    success { echo "Pipeline completed successfully ✅" }
    failure { echo "Pipeline failed ❌" }
  }
}
