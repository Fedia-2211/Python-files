# AWS EC2 + ALB Deployment with Tooplate Website

Automates deployment of an EC2 instance with an Application Load Balancer (ALB) and deploys a Tooplate website template.

---

## 🌐 Website Template
Template: **Moso Interior**  
Source: [Tooplate](https://www.tooplate.com/zip-templates/2133_moso_interior.zip)

---

## ⚡ Features
- Automatically detects your public IP for SSH
- Creates EC2 key pair & security groups
- Launches Amazon Linux 2023 EC2 instance
- Installs Apache, wget, unzip
- Downloads and deploys Tooplate template
- Creates an ALB and registers the EC2 instance
- Provides fallback page if download fails
- Prints all access information

---

## 🛠 Prerequisites
- Python 3.8+
- AWS CLI configured with credentials (`aws configure`)
- `boto3` and `requests` installed

```bash
pip install -r requirements.txt
