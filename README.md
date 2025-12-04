# Multi-Region 3-Tier Cloud-Native Platform

## Project Overview
This project implements a **3-Tier Multi-Region Cloud-Native Platform** with **CI/CD automation, containerization, and observability**. The platform is designed for high availability, scalability, and security using modern DevOps practices.  

**Key Features:**
- 3-Tier architecture: Web/API, Application, Data layers  
- Multi-region deployment for high availability and disaster recovery  
- **CI/CD pipeline** using Jenkins with automated testing, vulnerability scanning, and rollback  
- Containerized using **Docker** and deployed on **Amazon EKS (Kubernetes)**  
- **Observability** with **Prometheus**, **Grafana**, and monitoring dashboards  
- Predictive scaling for cost optimization and load handling  

---

## Architecture Flow (Textual Representation)

                ┌───────────────┐
                │     User       │
                └───────▲───────┘
                        │
                        │
                ┌───────────────┐
                │   Developer    │
                └───────▲───────┘
                        │
                        │  (SCM Commit / Push)
                        ▼
                ┌──────────────────────┐
                │   Source Control (SCM│
                │   e.g. GitHub/GitLab)│
                └─────────▲────────────┘
                          │
                          │
                ┌─────────┴───────────┐
                │ Jenkins Multi-Pipeline│
                │  - Build              │
                │  - Test               │
                │  - Deploy             │
                └─────────▲───────────┘
                          │
                          │
          ┌───────────────┴───────────────┐
          │   Docker (Image Build)         │
          │   Trivy (Image + SCM Scan)     │
          └───────────────▲───────────────┘
                          │
                          │
                ┌─────────┴───────────┐
                │ AWS ECR (Image Repo)│
                └─────────▲───────────┘
                          │
                          │
        ┌─────────────────┴─────────────────┐
        │   AWS EKS (Multi-Region Clusters) │
        │   Region A   Region B   Region C  │
        │                                   │
        │   ┌──────────┐ ┌──────────┐ ┌──────────┐
        │   │ Web Tier │ │ Web Tier │ │ Web Tier │
        │   └──────────┘ └──────────┘ └──────────┘
        │   ┌──────────┐ ┌──────────┐ ┌──────────┐
        │   │ App Tier │ │ App Tier │ │ App Tier │
        │   └──────────┘ └──────────┘ └──────────┘
        │   ┌────────────┐ ┌────────────┐ ┌────────────┐
        │   │ DB Tier    │ │ DB Tier    │ │ DB Tier    │
        │   └────────────┘ └────────────┘ └────────────┘
        └─────────────────▲─────────────────┘
                          │
                          │
                ┌─────────┴───────────┐
                │ Prometheus (Metrics)│
                └─────────▲───────────┘
                          │
                          │
                ┌─────────┴───────────┐
                │ Grafana (Dashboards)│
                └─────────────────────┘
---

## End‑to‑End Architecture Diagram
![Architecture Diagram](project-screenshot/end‑to‑end architecture diagram.PNG).


**Multi-Region Deployment:**  
The application is deployed across multiple AWS regions using Terraform modules for networking, EKS clusters, and data services.

---

## CI/CD Pipeline (Jenkins)
![Architecture Diagram](project-screenshot/end‑to‑end architecture diagram.PNG)  

The pipeline automates **code quality checks, image building, security scanning, deployment, and monitoring**.

## Pipeline Screenshot
![Pipeline Screenshot ](project-screenshot/Jenkins-pipeline.PNG)


| Stage | Description | Approx Duration |
|-------|-------------|----------------|
| Checkout SCM | Clone repository | 27s |
| Tooling Check | Verify tools and versions | 4.3s |
| Pre-commit & Format | Run pre-commit hooks and format code | 3.1s |
| Install Dev Dependencies | Install project dependencies | 2.2s |
| Lint | Static code analysis | 3.3s |
| Unit Tests & Coverage | Run unit tests and check code coverage | 3.1s |
| Build Docker Image | Build container image | 18s |
| Update Trivy DB | Update vulnerability database | 1m 25s |
| Generate SBOM (Syft) | Create software bill of materials | 3.6s |
| Trivy Vulnerability Scan | Scan container for vulnerabilities | 5m 7s |
| Push to ECR Multi-Region | Push image to ECR in multiple regions | 59s |
| Deploy to EKS | Deploy services to Kubernetes | 7.1s |
| Monitoring Namespace | Setup monitoring namespace | 36s |
| Monitoring ServiceAccounts | Configure service accounts | 22s |
| Monitoring RBAC | Apply RBAC policies for monitoring | 18s |
| Monitoring Datasource | Configure Prometheus/Grafana data sources | 14s |
| Observability & Predictive Scaling | Setup dashboards and predictive scaling | 3.7s |
| Cleanup Docker Images | Remove local images to free space | 26s |
| Post Actions | Final notifications and cleanup | 2.2s |

> **Rollback:** The pipeline supports automated rollback if deployment or health checks fail.

---

## Observability & Monitoring

- **Prometheus**: Metrics collection from Kubernetes pods and nodes  
- **Grafana**: Dashboards for application performance and resource utilization  
- **Predictive Scaling**: Autoscaling based on historical metrics for optimized cost and performance

## Observability & Monitoring Dashboard
![Observability & Monitoring Dashboard ](project-screenshot/App-Dashborad.PNG)

---

## Getting Started

### Prerequisites
- **Terraform** ≥ 1.5  
- **Jenkins** with pipeline plugins  
- **Docker** ≥ 20.x  
- **kubectl** and AWS CLI configured for EKS  
- Access to AWS ECR for image storage  

### Installation Steps
1. Clone the repository:
```bash
git clone <company-repo-url>
cd <repo-folder>
```


## Initialize Terraform modules:

cd infra
terraform init
terraform plan
terraform apply


**Build and deploy services via Jenkins pipeline (or manually if required)**

Access monitoring dashboards via Grafana

## Repo Structure
repo-root/
├─ infra/               # Terraform modules & environment configs
├─ services/            # Application services
├─ k8s/                 # Kubernetes manifests / Helm charts
├─ monitoring/          # Prometheus, Grafana, dashboards
├─ scripts/             # Utility scripts (coverage, metrics, predictive scaling)
├─ Jenkinsfile          # Pipeline configuration
└─ README.md

## Security & Compliance

Pre-commit hooks for formatting and linting

Unit tests with coverage checks before merge

SBOM generation with Syft

Container vulnerability scanning with Trivy

Branch protection and code reviews enforced

## Future Enhancements

Integrate Blue-Green / Canary deployments via Istio or Argo Rollouts

Extend predictive scaling with advanced ML models

Add multi-cloud support beyond AWS.

**Author**

Emmanuela
Cloud Architect & DevOps Engineer
GitHub: https://github.com/Cloud-Architect-Emma

⭐ Support the Project

If this repo helps you, please star it.
It improves visibility for other DevOps/Cloud Engineers.
