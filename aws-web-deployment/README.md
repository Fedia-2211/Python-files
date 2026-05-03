# 🚀 AWS EC2 + ALB Deployment with Tooplate Website

Automates the deployment of an **EC2 instance** with an **Application Load Balancer (ALB)** and deploys a **Tooplate website template**.  

This project demonstrates **AWS Infrastructure as Code (IaC)** with a real website template for testing and learning.

---

## 🌐 Website Template
- **Template Name:** Moso Interior  
- **Source:** [Tooplate](https://www.tooplate.com/zip-templates/2133_moso_interior.zip)

---

## ⚡ Features
- Detects your **public IP** for secure SSH access
- Creates **EC2 key pair** and **security groups**
- Launches **Amazon Linux 2023 EC2 instance**
- Installs Apache, wget, unzip
- Downloads and deploys the Tooplate template automatically
- Creates an **ALB** and registers the EC2 instance
- Provides a **fallback page** if the template download fails
- Prints **all access information** after deployment

---

## 🛠 Prerequisites
- **Python 3.8+**
- **AWS CLI** configured with credentials (`aws configure`)
- Python libraries:
  ```bash
  pip install -r requirements.txt
