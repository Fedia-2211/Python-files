#!/usr/bin/env python3
"""
AWS Infrastructure Deployment with Tooplate Website
Description: Automatically deploys EC2 instance with ALB and deploys Tooplate website template
Website: https://www.tooplate.com/zip-templates/2133_moso_interior.zip
"""

import boto3
import time
import base64
import requests
import sys
import os
from datetime import datetime

# ===== CONFIGURATION =====
TEMPLATE_NAME = "moso-interior"  # From tooplate template
TOOPLATE_URL = "https://www.tooplate.com/zip-templates/2133_moso_interior.zip"
REGION = "us-east-1"  # Change as needed

# ===== HELPER FUNCTIONS =====
def print_section(message):
    """Print formatted section header"""
    print("\n" + "="*70)
    print(f"📌 {message}")
    print("="*70)

def print_success(message):
    """Print success message"""
    print(f"✅ {message}")

def print_error(message):
    """Print error message"""
    print(f"❌ {message}")

def print_info(message):
    """Print info message"""
    print(f"ℹ️  {message}")

def get_my_ip():
    """Get public IP address"""
    try:
        ip = requests.get('https://checkip.amazonaws.com', timeout=5).text.strip()
        print_info(f"Detected your public IP: {ip}")
        return f"{ip}/32"
    except:
        print_info("Could not detect IP automatically")
        ip = input("Enter your public IP address (e.g., ####.####.####.####/32): ")
        return f"{ip}/32"

def create_key_pair(ec2, key_name):
    """Create EC2 key pair"""
    try:
        ec2.describe_key_pairs(KeyNames=[key_name])
        print_info(f"Key pair '{key_name}' already exists. Using existing key.")
        return True
    except:
        try:
            key_pair = ec2.create_key_pair(KeyName=key_name)
            with open(f"{key_name}.pem", 'w') as key_file:
                key_file.write(key_pair['KeyMaterial'])
            os.chmod(f"{key_name}.pem", 0o400)
            print_success(f"Key pair created and saved to {key_name}.pem")
            return True
        except Exception as e:
            print_error(f"Failed to create key pair: {e}")
            return False

def create_security_group(ec2, sg_name, vpc_id, my_ip):
    """Create security group for EC2 instance"""
    try:
        # Check if security group exists
        try:
            sg_response = ec2.describe_security_groups(GroupNames=[sg_name])
            sg_id = sg_response['SecurityGroups'][0]['GroupId']
            print_info(f"Security group '{sg_name}' already exists with ID: {sg_id}")
            return sg_id
        except:
            # Create new security group
            sg_response = ec2.create_security_group(
                GroupName=sg_name,
                Description=f"Security group for {TEMPLATE_NAME} website",
                VpcId=vpc_id
            )
            sg_id = sg_response['GroupId']
            print_success(f"Security group created: {sg_id}")
            
            # Add SSH rule (port 22 from my IP)
            ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[{
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': my_ip, 'Description': 'SSH from my IP'}]
                }]
            )
            
            # Add HTTP rule (port 80 from anywhere)
            ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[{
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTP from anywhere'}]
                }]
            )
            print_success("Security group rules added successfully")
            return sg_id
    except Exception as e:
        print_error(f"Failed to create security group: {e}")
        sys.exit(1)

def create_alb_security_group(ec2, alb_sg_name, vpc_id):
    """Create security group for ALB"""
    try:
        try:
            alb_sg_response = ec2.describe_security_groups(GroupNames=[alb_sg_name])
            alb_sg_id = alb_sg_response['SecurityGroups'][0]['GroupId']
            print_info(f"ALB security group already exists with ID: {alb_sg_id}")
            return alb_sg_id
        except:
            alb_sg_response = ec2.create_security_group(
                GroupName=alb_sg_name,
                Description=f"Security group for ALB of {TEMPLATE_NAME}",
                VpcId=vpc_id
            )
            alb_sg_id = alb_sg_response['GroupId']
            print_success(f"ALB security group created: {alb_sg_id}")
            
            # Allow port 80 from anywhere on ALB
            ec2.authorize_security_group_ingress(
                GroupId=alb_sg_id,
                IpPermissions=[{
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTP from anywhere'}]
                }]
            )
            print_success("ALB security group rules added")
            return alb_sg_id
    except Exception as e:
        print_error(f"Failed to create ALB security group: {e}")
        sys.exit(1)

def get_latest_amazon_linux_ami(ec2):
    """Get the latest Amazon Linux 2023 AMI"""
    print_info("Finding latest Amazon Linux 2023 AMI...")
    try:
        ami_response = ec2.describe_images(
            Owners=['amazon'],
            Filters=[
                {'Name': 'name', 'Values': ['al2023-ami-2023.*-x86_64']},
                {'Name': 'state', 'Values': ['available']}
            ]
        )
        ami_id = sorted(ami_response['Images'], key=lambda x: x['CreationDate'], reverse=True)[0]['ImageId']
        print_success(f"Using AMI: {ami_id}")
        return ami_id
    except Exception as e:
        print_error(f"Failed to get AMI: {e}")
        sys.exit(1)

def get_free_tier_instance_type(ec2):
    """Get Free Tier eligible instance type"""
    print_info("Checking Free Tier eligible instance types...")
    try:
        instance_types = ec2.describe_instance_types(
            Filters=[
                {'Name': 'free-tier-eligible', 'Values': ['true']},
                {'Name': 'processor-info.supported-architecture', 'Values': ['x86_64']}
            ]
        )
        
        eligible_types = [it['InstanceType'] for it in instance_types['InstanceTypes']]
        print_info(f"Available Free Tier types: {', '.join(eligible_types[:5])}")
        
        # Prefer t3.micro or t2.micro
        for preferred in ['t3.micro', 't2.micro']:
            if preferred in eligible_types:
                print_success(f"Using instance type: {preferred}")
                return preferred
        
        instance_type = eligible_types[0] if eligible_types else 't3.micro'
        print_success(f"Using instance type: {instance_type}")
        return instance_type
    except Exception as e:
        print_info(f"Could not check Free Tier types, using t3.micro: {e}")
        return 't3.micro'

def create_userdata_script():
    """Create userdata script to download and deploy Tooplate website"""
    
    userdata_script = f"""#!/bin/bash
# Auto-deployment script for Tooplate website
# Template: {TEMPLATE_NAME}
# Source: {TOOPLATE_URL}

# Log all output
exec > >(tee /var/log/userdata.log|logger -t userdata) 2>&1
echo "Starting user data script at $(date)"

# Update system
echo "Updating system packages..."
dnf update -y

# Install required packages
echo "Installing httpd, wget, and unzip..."
dnf install -y httpd wget unzip

# Start and enable httpd
echo "Starting httpd service..."
systemctl start httpd
systemctl enable httpd

# Create temporary directory for download
echo "Creating temporary directory..."
mkdir -p /tmp/tooplate
cd /tmp/tooplate

# Download Tooplate template
echo "Downloading Tooplate template from {TOOPLATE_URL}..."
wget --timeout=30 --tries=3 {TOOPLATE_URL} -O template.zip

if [ $? -eq 0 ]; then
    echo "Download successful, extracting template..."
    unzip -o template.zip
    
    # Find the extracted directory
    EXTRACTED_DIR=$(find . -maxdepth 1 -type d -name "2133*" | head -1)
    
    if [ -n "$EXTRACTED_DIR" ]; then
        echo "Copying files to /var/www/html..."
        # Remove default index.html
        rm -rf /var/www/html/*
        # Copy extracted files
        cp -r $EXTRACTED_DIR/* /var/www/html/
        echo "Tooplate template deployed successfully!"
    else
        echo "ERROR: Could not find extracted directory"
        # Fallback to sample page
        create_fallback_page
    fi
else
    echo "ERROR: Failed to download template from Tooplate"
    create_fallback_page
fi

# Clean up
echo "Cleaning up temporary files..."
rm -rf /tmp/tooplate

# Set proper permissions
echo "Setting permissions..."
chown -R apache:apache /var/www/html
chmod -R 755 /var/www/html

# Restart httpd to apply changes
echo "Restarting httpd..."
systemctl restart httpd

echo "User data script completed at $(date)"

# Function to create fallback page if download fails
create_fallback_page() {{
    cat > /var/www/html/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{TEMPLATE_NAME} - AWS Deployment</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 800px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
        }}
        h1 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 2.5em;
        }}
        .status {{
            background: #4CAF50;
            color: white;
            padding: 10px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .info {{
            background: #f0f0f0;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: left;
        }}
        .info h3 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        .instance-details {{
            font-family: monospace;
            font-size: 14px;
            color: #555;
            margin-top: 20px;
            padding: 10px;
            background: #e8e8e8;
            border-radius: 5px;
        }}
        footer {{
            margin-top: 30px;
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 {TEMPLATE_NAME}</h1>
        <div class="status">
            ✅ Website Deployed Successfully on AWS!
        </div>
        <div class="info">
            <h3>📋 Deployment Information</h3>
            <p><strong>Template:</strong> {TEMPLATE_NAME}</p>
            <p><strong>Deployment Time:</strong> $(date)</p>
            <p><strong>Instance ID:</strong> $(curl -s http://169.254.169.254/latest/meta-data/instance-id)</p>
            <p><strong>Availability Zone:</strong> $(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)</p>
            <p><strong>Instance Type:</strong> $(curl -s http://169.254.169.254/latest/meta-data/instance-type)</p>
        </div>
        <div class="instance-details">
            <strong>Note:</strong> The Tooplate template download is being processed. 
            This fallback page will be replaced once the template is fully deployed.
        </div>
        <footer>
            Deployed using AWS Infrastructure as Code | Powered by Tooplate
        </footer>
    </div>
</body>
</html>
EOF
}}
"""
    return userdata_script

def launch_ec2_instance(ec2, ami_id, instance_type, key_name, sg_id, instance_name, userdata_encoded):
    """Launch EC2 instance with userdata"""
    print_info(f"Launching EC2 instance: {instance_name}")
    try:
        run_response = ec2.run_instances(
            ImageId=ami_id,
            InstanceType=instance_type,
            KeyName=key_name,
            SecurityGroupIds=[sg_id],
            UserData=userdata_encoded,
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value': instance_name},
                    {'Key': 'Template', 'Value': TEMPLATE_NAME},
                    {'Key': 'DeploymentDate', 'Value': datetime.now().strftime('%Y-%m-%d')}
                ]
            }]
        )
        
        instance_id = run_response['Instances'][0]['InstanceId']
        print_success(f"Instance launched with ID: {instance_id}")
        
        # Wait for instance to be running
        print_info("Waiting for instance to be running...")
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])
        print_success("Instance is running")
        
        # Get instance details
        instance_info = ec2.describe_instances(InstanceIds=[instance_id])
        instance_ip = instance_info['Reservations'][0]['Instances'][0]['PrivateIpAddress']
        public_ip = instance_info['Reservations'][0]['Instances'][0].get('PublicIpAddress', 'N/A')
        
        return instance_id, instance_ip, public_ip
    except Exception as e:
        print_error(f"Failed to launch instance: {e}")
        sys.exit(1)

def create_target_group(elbv2, tg_name, vpc_id):
    """Create target group for ALB"""
    print_info(f"Creating target group: {tg_name}")
    try:
        tg_response = elbv2.create_target_group(
            Name=tg_name[:32],
            Protocol='HTTP',
            Port=80,
            VpcId=vpc_id,
            HealthCheckProtocol='HTTP',
            HealthCheckPath='/',
            HealthCheckIntervalSeconds=30,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=2,
            UnhealthyThresholdCount=2
        )
        tg_arn = tg_response['TargetGroups'][0]['TargetGroupArn']
        print_success(f"Target group created: {tg_arn}")
        return tg_arn
    except Exception as e:
        if 'already exists' in str(e).lower():
            tg_response = elbv2.describe_target_groups(Names=[tg_name[:32]])
            tg_arn = tg_response['TargetGroups'][0]['TargetGroupArn']
            print_info(f"Target group already exists with ARN: {tg_arn}")
            return tg_arn
        else:
            print_error(f"Failed to create target group: {e}")
            sys.exit(1)

def create_load_balancer(elbv2, alb_name, subnet_ids, alb_sg_id):
    """Create Application Load Balancer"""
    print_info(f"Creating Application Load Balancer: {alb_name}")
    try:
        alb_response = elbv2.create_load_balancer(
            Name=alb_name[:32],
            Subnets=subnet_ids,
            SecurityGroups=[alb_sg_id],
            Scheme='internet-facing',
            Type='application',
            Tags=[{'Key': 'Name', 'Value': alb_name}]
        )
        alb_arn = alb_response['LoadBalancers'][0]['LoadBalancerArn']
        print_success(f"ALB created: {alb_arn}")
        
        # Wait for ALB to be active
        print_info("Waiting for ALB to be active (this may take 1-2 minutes)...")
        waiter = elbv2.get_waiter('load_balancer_available')
        waiter.wait(LoadBalancerArns=[alb_arn])
        print_success("ALB is active")
        
        return alb_arn
    except Exception as e:
        if 'already exists' in str(e).lower():
            alb_response = elbv2.describe_load_balancers(Names=[alb_name[:32]])
            alb_arn = alb_response['LoadBalancers'][0]['LoadBalancerArn']
            print_info(f"ALB already exists with ARN: {alb_arn}")
            return alb_arn
        else:
            print_error(f"Failed to create ALB: {e}")
            sys.exit(1)

def create_listener(elbv2, alb_arn, tg_arn):
    """Create listener for ALB"""
    print_info("Creating listener...")
    try:
        elbv2.create_listener(
            LoadBalancerArn=alb_arn,
            Protocol='HTTP',
            Port=80,
            DefaultActions=[{
                'Type': 'forward',
                'TargetGroupArn': tg_arn
            }]
        )
        print_success("Listener created successfully")
    except Exception as e:
        if 'already exists' in str(e).lower():
            print_info("Listener already exists")
        else:
            print_error(f"Warning: Could not create listener - {e}")

# ===== MAIN FUNCTION =====
def main():
    """Main deployment function"""
    
    print_section("AWS INFRASTRUCTURE DEPLOYMENT WITH TOOPLATE WEBSITE")
    print_info(f"Template: {TEMPLATE_NAME}")
    print_info(f"Source: {TOOPLATE_URL}")
    print_info(f"Region: {REGION}")
    
    # Initialize AWS clients
    try:
        ec2 = boto3.client('ec2', region_name=REGION)
        elbv2 = boto3.client('elbv2', region_name=REGION)
        print_success("AWS clients initialized successfully")
    except Exception as e:
        print_error(f"Failed to initialize AWS clients: {e}")
        print_info("Make sure you have configured AWS credentials using 'aws configure'")
        sys.exit(1)
    
    # Get configuration
    my_ip = get_my_ip()
    
    # Get default VPC
    print_info("Getting default VPC...")
    default_vpc = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
    vpc_id = default_vpc['Vpcs'][0]['VpcId']
    print_success(f"Using VPC: {vpc_id}")
    
    # Step 1: Create key pair
    print_section("STEP 1: Creating Key Pair")
    key_name = f"{TEMPLATE_NAME}-key"
    if not create_key_pair(ec2, key_name):
        sys.exit(1)
    
    # Step 2: Create security groups
    print_section("STEP 2: Creating Security Groups")
    sg_name = f"{TEMPLATE_NAME}-sg"
    sg_id = create_security_group(ec2, sg_name, vpc_id, my_ip)
    
    alb_sg_name = f"{TEMPLATE_NAME}-alb-sg"
    alb_sg_id = create_alb_security_group(ec2, alb_sg_name, vpc_id)
    
    # Step 3: Launch EC2 instance
    print_section("STEP 3: Launching EC2 Instance")
    ami_id = get_latest_amazon_linux_ami(ec2)
    instance_type = get_free_tier_instance_type(ec2)
    userdata_script = create_userdata_script()
    userdata_encoded = base64.b64encode(userdata_script.encode('utf-8')).decode('utf-8')
    instance_name = f"{TEMPLATE_NAME}-ec2"
    
    instance_id, instance_ip, public_ip = launch_ec2_instance(
        ec2, ami_id, instance_type, key_name, sg_id, instance_name, userdata_encoded
    )
    
    # Step 4: Create ALB infrastructure
    print_section("STEP 4: Creating Load Balancer Infrastructure")
    
    # Get all subnets
    subnets_response = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
    subnet_ids = [subnet['SubnetId'] for subnet in subnets_response['Subnets']]
    print_info(f"Using {len(subnet_ids)} subnets across all availability zones")
    
    # Create target group
    tg_name = f"{TEMPLATE_NAME}-tg"
    tg_arn = create_target_group(elbv2, tg_name, vpc_id)
    
    # Register instance
    print_info("Registering instance to target group...")
    elbv2.register_targets(TargetGroupArn=tg_arn, Targets=[{'Id': instance_id, 'Port': 80}])
    print_success("Instance registered successfully")
    
    # Create ALB
    alb_name = f"{TEMPLATE_NAME}-alb"
    alb_arn = create_load_balancer(elbv2, alb_name, subnet_ids, alb_sg_id)
    
    # Create listener
    create_listener(elbv2, alb_arn, tg_arn)
    
    # Get ALB DNS name
    alb_dns = elbv2.describe_load_balancers(LoadBalancerArns=[alb_arn])['LoadBalancers'][0]['DNSName']
    
    # Step 5: Print results
    print_section("DEPLOYMENT COMPLETED SUCCESSFULLY!")
    print(f"📊 Deployment Summary:")
    print(f"   • Template: {TEMPLATE_NAME}")
    print(f"   • Source: {TOOPLATE_URL}")
    print(f"   • Region: {REGION}")
    print(f"   • Instance ID: {instance_id}")
    print(f"   • Instance Type: {instance_type}")
    print(f"   • Security Group ID: {sg_id}")
    print(f"   • ALB DNS Endpoint: http://{alb_dns}")
    
    print_section("ACCESS INFORMATION")
    print(f"🌐 Website URL: http://{alb_dns}")
    if public_ip != 'N/A':
        print(f"🔧 Direct Instance Access (for testing): http://{public_ip}")
    print(f"📝 Note: It will take 2-3 minutes for the website to be fully deployed")
    
    print_section("USEFUL COMMANDS")
    print(f"# Check instance health:")
    print(f"aws elbv2 describe-target-health --target-group-arn {tg_arn}")
    print(f"\n# SSH into instance (if needed):")
    print(f"ssh -i {key_name}.pem ec2-user@{public_ip if public_ip != 'N/A' else '<public-ip>'}")
    print(f"\n# View userdata logs on instance:")
    print(f"sudo cat /var/log/userdata.log")
    
    print_section("CLEANUP")
    print(f"To delete all resources, run: python cleanup_aws_resources.py")
    print("="*70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


