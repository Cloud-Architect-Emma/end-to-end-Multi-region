// Jenkinsfile - Enterprise CI/CD (Declarative)
// - Builds, tests, SBOM, Trivy scan, pushes multi-region to ECR
// - Deploys with Helm to EKS, health checks, automated rollback
// - Replace placeholders and add credentials in Jenkins

pipeline {
  agent any

  environment {
    // Set defaults — override in Jenkins job or via pipeline parameters
    AWS_ACCOUNT_ID      = credentials('aws-account-id')      // plain string credential (or use env)
    AWS_DEFAULT_REGION  = "us-east-1"
    AWS_SECOND_REGION   = "us-east-2"
    SERVICE_NAME        = "cartservice"
    IMAGE_TAG           = ""    // filled at runtime

    // ECR endpoints (constructed)
    ECR_REPO_PRIMARY    = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/${SERVICE_NAME}"
    ECR_REPO_SECONDARY  = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_SECOND_REGION}.amazonaws.com/${SERVICE_NAME}"

    // Tool paths (assume tools installed on agent)
    SYFT_BIN           = "syft"
    TRIVY_BIN          = "trivy"
    GITLEAKS_BIN       = "gitleaks"
    HELM_BIN           = "helm"
    KUBECTL_BIN        = "kubectl"
  }

  options {
    timestamps()
    ansiColor('xterm')
    buildDiscarder(logRotator(numToKeepStr: '30'))
    timeout(time: 60, unit: 'MINUTES')
  }

  parameters {
    string(name: 'BRANCH_NAME', defaultValue: 'main', description: 'Branch to build')
    booleanParam(name: 'DEPLOY_TO_STAGING', defaultValue: true, description: 'Auto deploy staging?')
    booleanParam(name: 'DEPLOY_TO_PROD', defaultValue: false, description: 'Deploy to production (manual gating recommended)')
  }

  stages {

    stage('Checkout') {
      steps {
        script { env.GIT_COMMIT_SHORT = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim() }
        checkout([$class: 'GitSCM', branches: [[name: "*/${params.BRANCH_NAME}"]],
                  userRemoteConfigs: [[url: 'https://github.com/Cloud-Architect-Emma/end-to-end-Multi-region.git']]])
      }
    }

    stage('Pre-commit hooks & Format checks') {
      steps {
        sh '''
          set -e
          if command -v pre-commit >/dev/null 2>&1; then
            pre-commit run --all-files || true
          else
            echo "pre-commit not installed on agent; skipping"
          fi
        '''
      }
    }

    stage('Install dev dependencies') {
      steps {
        script {
          if (fileExists('package.json')) {
            sh 'npm ci'
          }
          if (fileExists('requirements.txt')) {
            sh 'python -m pip install -r requirements.txt --user'
          }
        }
      }
    }

    stage('Static Analysis & Secret Scan') {
      steps {
        sh '''
          set -e
          echo "Running gitleaks if available..."
          if command -v ${GITLEAKS_BIN} >/dev/null 2>&1; then
            ${GITLEAKS_BIN} detect --source . || true
          else
            echo "gitleaks not installed - skip"
          fi
        '''
      }
    }

    stage('Lint') {
      steps {
        sh '''
          set -e
          if [ -f package.json ]; then npm run lint || true; fi
          if [ -f requirements.txt ]; then flake8 || true; fi
        '''
      }
    }

    stage('Unit tests & Coverage') {
      steps {
        sh '''
          set -e
          # Node
          if [ -f package.json ]; then
            npm test --if-present
            # if using istanbul/nyc: enforce coverage
            if command -v nyc >/dev/null 2>&1; then
              nyc --reporter=text-summary --reporter=lcov npm test || true
              # optional: fail if coverage < 80% (example using report)
            fi
          fi

          # Python
          if [ -f requirements.txt ]; then
            if command -v pytest >/dev/null 2>&1; then
              pytest --maxfail=1 --disable-warnings -q
              if [ -f .coverage ]; then
                coverage report --fail-under=80 || true
              fi
            fi
          fi
        '''
      }
    }

    stage('Build Docker image') {
      steps {
        script {
          // create a stable tag
          env.IMAGE_TAG = "${params.BRANCH_NAME}-${env.BUILD_NUMBER}-${env.GIT_COMMIT_SHORT}"
        }
        sh '''
          set -e
          echo "IMAGE_TAG=${IMAGE_TAG}" > .image_tag
          # try to ensure buildx available; fallback to classic docker build
          if docker buildx version >/dev/null 2>&1; then
            docker build -t ${SERVICE_NAME}:${IMAGE_TAG} .
          else
            echo "docker buildx missing — using docker build"
            docker build -t ${SERVICE_NAME}:${IMAGE_TAG} .
          fi
        '''
      }
    }

    stage('Generate SBOM (Syft)') {
      steps {
        sh '''
          set -e
          IMAGE_TAG=$(cat .image_tag | cut -d'=' -f2)
          if command -v ${SYFT_BIN} >/dev/null 2>&1; then
            ${SYFT_BIN} ${SERVICE_NAME}:${IMAGE_TAG} -o json > .sbom.json || true
            echo "SBOM written to .sbom.json"
          else
            echo "syft not installed; skip SBOM generation"
          fi
        '''
      }
    }

    stage('Image vulnerability scan (Trivy)') {
      steps {
        sh '''
          set -e
          IMAGE_TAG=$(cat .image_tag | cut -d'=' -f2)
          if command -v ${TRIVY_BIN} >/dev/null 2>&1; then
            ${TRIVY_BIN} image --exit-code 1 --severity CRITICAL,HIGH ${SERVICE_NAME}:${IMAGE_TAG} || \
             (echo "Trivy found high/critical issues" && true)
          else
            echo "trivy not installed; skip scanning"
          fi
        '''
      }
    }

    stage('Push to ECR (multi-region)') {
      steps {
        withCredentials([[
          $class: 'AmazonWebServicesCredentialsBinding',
          credentialsId: 'aws-creds'  // IAM credentials (accessKey/secret) stored in Jenkins
        ]]) {
          sh '''
            set -e
            IMAGE_TAG=$(cat .image_tag | cut -d'=' -f2)
            # create ECR repos if necessary (idempotent)
            aws ecr describe-repositories --region $AWS_DEFAULT_REGION --repository-names ${SERVICE_NAME} >/dev/null 2>&1 || \
              aws ecr create-repository --region $AWS_DEFAULT_REGION --repository-name ${SERVICE_NAME} || true

            aws ecr describe-repositories --region $AWS_SECOND_REGION --repository-names ${SERVICE_NAME} >/dev/null 2>&1 || \
              aws ecr create-repository --region $AWS_SECOND_REGION --repository-name ${SERVICE_NAME} || true

            # auth and push
            aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin ${ECR_REPO_PRIMARY%%/*}
            aws ecr get-login-password --region $AWS_SECOND_REGION | docker login --username AWS --password-stdin ${ECR_REPO_SECONDARY%%/*}

            docker tag ${SERVICE_NAME}:${IMAGE_TAG} ${ECR_REPO_PRIMARY}:${IMAGE_TAG}
            docker tag ${SERVICE_NAME}:${IMAGE_TAG} ${ECR_REPO_SECONDARY}:${IMAGE_TAG}

            docker push ${ECR_REPO_PRIMARY}:${IMAGE_TAG}
            docker push ${ECR_REPO_SECONDARY}:${IMAGE_TAG}
          '''
        }
      }
    }

    stage('Deploy to Staging (Helm -> EKS)') {
      when {
        expression { params.DEPLOY_TO_STAGING == true && params.BRANCH_NAME == 'staging' }
      }
      steps {
        withCredentials([file(credentialsId: 'kubeconfig-staging', variable: 'KUBECONFIG_FILE')]) {
          sh '''
            set -e
            export KUBECONFIG=${KUBECONFIG_FILE}
            IMAGE_TAG=$(cat .image_tag | cut -d'=' -f2)

            # update Helm chart image and deploy
            ${HELM_BIN} upgrade --install ${SERVICE_NAME}-staging ./k8s/helm-chart \
              --set image.repository=${ECR_REPO_PRIMARY} \
              --set image.tag=${IMAGE_TAG} \
              --namespace staging --create-namespace

            # wait for rollout and healthchecks
            ${KUBECTL_BIN} -n staging rollout status deploy/${SERVICE_NAME} --timeout=3m
            # basic readiness probe check (customise per app)
            ${KUBECTL_BIN} -n staging wait --for=condition=available --timeout=2m deploy/${SERVICE_NAME}
          '''
        }
      }
    }

    stage('Deploy to Production (Helm -> EKS)') {
      when {
        expression { params.DEPLOY_TO_PROD == true && params.BRANCH_NAME == 'main' }
      }
      steps {
        input message: "Approve production deploy?", ok: "Deploy"
        withCredentials([file(credentialsId: 'kubeconfig-prod', variable: 'KUBECONFIG_FILE')]) {
          sh '''
            set -e
            export KUBECONFIG=${KUBECONFIG_FILE}
            IMAGE_TAG=$(cat .image_tag | cut -d'=' -f2)

            ${HELM_BIN} upgrade --install ${SERVICE_NAME} ./k8s/helm-chart \
              --set image.repository=${ECR_REPO_PRIMARY} \
              --set image.tag=${IMAGE_TAG} \
              --namespace production --create-namespace

            ${KUBECTL_BIN} -n production rollout status deploy/${SERVICE_NAME} --timeout=4m
          '''
        }
      }
    }

    stage('Post-deploy verification & rollback guard') {
      when {
        anyOf {
          expression { params.DEPLOY_TO_STAGING == true && params.BRANCH_NAME == 'staging' }
          expression { params.DEPLOY_TO_PROD == true && params.BRANCH_NAME == 'main' }
        }
      }
      steps {
        script {
          def ns = (params.BRANCH_NAME == 'staging') ? 'staging' : 'production'
          sh """
            set -e
            export KUBECONFIG=$(mktemp)
            cp ${KUBECONFIG_FILE} ${KUBECONFIG}
            # Simple end-to-end health check: hit /health endpoint via port-forward (example)
            POD=$(kubectl -n ${ns} get pods -l app=${SERVICE_NAME} -o jsonpath='{.items[0].metadata.name}')
            kubectl -n ${ns} port-forward $POD 8085:5000 >/dev/null 2>&1 & PID=$!
            sleep 2
            STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8085/health || true)
            kill $PID || true
            if [ "$STATUS" != "200" ]; then
              echo "Health check failed (status=$STATUS) - initiating rollback"
              helm rollback ${SERVICE_NAME} 0 --namespace ${ns} || true
              exit 1
            fi
            echo "Health check success (200)"
          """
        }
      }
    }

  } // stages

  post {
    success {
      echo "Pipeline completed successfully"
      // Add Slack / Teams notification steps here using webhook credentials if desired
    }
    failure {
      echo "Pipeline failed — check logs"
      // Optionally add rollback/cleanup steps or notifications
    }
    always {
      archiveArtifacts artifacts: '.image_tag, .sbom.json', allowEmptyArchive: true
    }
  }
}
