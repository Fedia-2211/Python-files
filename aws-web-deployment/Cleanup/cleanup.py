import boto3
import time

# ===== CONFIGURATION =====
TEMPLATE_NAME = "toolplate-website-template"  # Must match the name used in setup
REGION = "us-east-1"  # Must match the region used in setup

# Initialize AWS clients
ec2 = boto3.client('ec2', region_name=REGION)
elbv2 = boto3.client('elbv2', region_name=REGION)
autoscaling = boto3.client('autoscaling', region_name=REGION)  # Just in case

# ===== RESOURCE NAMES =====
KEY_NAME = f"{TEMPLATE_NAME}-key"
EC2_SG_NAME = f"{TEMPLATE_NAME}-sg"
ALB_SG_NAME = f"{TEMPLATE_NAME}-alb-sg"
INSTANCE_NAME = f"{TEMPLATE_NAME}-ec2"
ALB_NAME = f"{TEMPLATE_NAME}-alb"[:32]  # Max 32 characters
TG_NAME = f"{TEMPLATE_NAME}-tg"[:32]    # Max 32 characters

print("="*70)
print("🧹 AWS RESOURCE CLEANUP SCRIPT")
print("="*70)
print(f"Template Name: {TEMPLATE_NAME}")
print(f"Region: {REGION}")
print("="*70)

# Confirm before deletion
print("\n⚠️  WARNING: This will delete all resources created by the setup script!")
confirm = input("Are you sure you want to continue? (yes/no): ")
if confirm.lower() != 'yes':
    print("Cleanup cancelled.")
    exit()

# ===== 1. DELETE LOAD BALANCER =====
print("\n📌 Step 1: Deleting Application Load Balancer...")
try:
    # Find ALB
    albs = elbv2.describe_load_balancers(Names=[ALB_NAME])
    for alb in albs['LoadBalancers']:
        alb_arn = alb['LoadBalancerArn']
        print(f"  Found ALB: {alb['LoadBalancerName']} ({alb_arn})")
        
        # Delete listeners first
        listeners = elbv2.describe_listeners(LoadBalancerArn=alb_arn)
        for listener in listeners['Listeners']:
            print(f"  Deleting listener: {listener['ListenerArn']}")
            elbv2.delete_listener(ListenerArn=listener['ListenerArn'])
        
        # Delete ALB
        print(f"  Deleting ALB: {alb['LoadBalancerName']}")
        elbv2.delete_load_balancer(LoadBalancerArn=alb_arn)
        print(f"  ✅ ALB deleted successfully")
        
        # Wait for ALB deletion
        print("  Waiting for ALB to be deleted...")
        time.sleep(10)
except Exception as e:
    if 'not found' in str(e).lower():
        print("  ℹ️  ALB not found - skipping")
    else:
        print(f"  ⚠️  Error deleting ALB: {e}")

# ===== 2. DELETE TARGET GROUP =====
print("\n📌 Step 2: Deleting Target Group...")
try:
    tgs = elbv2.describe_target_groups(Names=[TG_NAME])
    for tg in tgs['TargetGroups']:
        tg_arn = tg['TargetGroupArn']
        print(f"  Found Target Group: {tg['TargetGroupName']} ({tg_arn})")
        
        # Deregister all targets
        targets = elbv2.describe_target_health(TargetGroupArn=tg_arn)
        if targets['TargetHealthDescriptions']:
            target_ids = [{'Id': t['Target']['Id']} for t in targets['TargetHealthDescriptions']]
            print(f"  Deregistering targets: {target_ids}")
            elbv2.deregister_targets(TargetGroupArn=tg_arn, Targets=target_ids)
            time.sleep(5)
        
        # Delete target group
        print(f"  Deleting Target Group: {tg['TargetGroupName']}")
        elbv2.delete_target_group(TargetGroupArn=tg_arn)
        print(f"  ✅ Target Group deleted successfully")
except Exception as e:
    if 'not found' in str(e).lower():
        print("  ℹ️  Target Group not found - skipping")
    else:
        print(f"  ⚠️  Error deleting Target Group: {e}")

# ===== 3. TERMINATE EC2 INSTANCES =====
print("\n📌 Step 3: Terminating EC2 instances...")
try:
    # Find instances with the specific tag
    instances = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:Name', 'Values': [INSTANCE_NAME]},
            {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}
        ]
    )
    
    instance_ids = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])
            print(f"  Found Instance: {instance['InstanceId']} - {instance.get('Tags', [])}")
    
    if instance_ids:
        print(f"  Terminating instances: {instance_ids}")
        ec2.terminate_instances(InstanceIds=instance_ids)
        print(f"  ✅ Instances terminated successfully")
        
        # Wait for termination
        print("  Waiting for instances to terminate...")
        waiter = ec2.get_waiter('instance_terminated')
        waiter.wait(InstanceIds=instance_ids)
        print("  ✅ All instances terminated")
    else:
        print("  ℹ️  No instances found with the specified name tag")
except Exception as e:
    print(f"  ⚠️  Error terminating instances: {e}")

# ===== 4. DELETE SECURITY GROUPS =====
print("\n📌 Step 4: Deleting security groups...")

# Function to delete security group with retry
def delete_security_group(sg_id, sg_name):
    try:
        # First, try to remove all ingress rules
        try:
            ec2.revoke_security_group_ingress(GroupId=sg_id, IpPermissions=[])
        except:
            pass
        
        # Delete the security group
        ec2.delete_security_group(GroupId=sg_id)
        print(f"  ✅ Security group '{sg_name}' ({sg_id}) deleted successfully")
        return True
    except Exception as e:
        if 'dependent' in str(e).lower() or 'in use' in str(e).lower():
            print(f"  ⚠️  Security group '{sg_name}' is still in use. Waiting...")
            time.sleep(10)
            try:
                ec2.delete_security_group(GroupId=sg_id)
                print(f"  ✅ Security group '{sg_name}' ({sg_id}) deleted successfully")
                return True
            except:
                print(f"  ❌ Could not delete security group '{sg_name}' - it may have dependencies")
                return False
        elif 'not found' in str(e).lower():
            print(f"  ℹ️  Security group '{sg_name}' not found")
            return True
        else:
            print(f"  ⚠️  Error deleting security group '{sg_name}': {e}")
            return False

# Delete EC2 security group
print(f"  Deleting EC2 security group: {EC2_SG_NAME}")
try:
    sg_response = ec2.describe_security_groups(GroupNames=[EC2_SG_NAME])
    sg_id = sg_response['SecurityGroups'][0]['GroupId']
    delete_security_group(sg_id, EC2_SG_NAME)
except Exception as e:
    if 'not found' in str(e).lower():
        print("  ℹ️  EC2 security group not found")
    else:
        print(f"  ⚠️  Error: {e}")

# Delete ALB security group
print(f"\n  Deleting ALB security group: {ALB_SG_NAME}")
try:
    alb_sg_response = ec2.describe_security_groups(GroupNames=[ALB_SG_NAME])
    alb_sg_id = alb_sg_response['SecurityGroups'][0]['GroupId']
    delete_security_group(alb_sg_id, ALB_SG_NAME)
except Exception as e:
    if 'not found' in str(e).lower():
        print("  ℹ️  ALB security group not found")
    else:
        print(f"  ⚠️  Error: {e}")

# ===== 5. DELETE KEY PAIR =====
print("\n📌 Step 5: Deleting key pair...")
try:
    ec2.delete_key_pair(KeyName=KEY_NAME)
    print(f"  ✅ Key pair '{KEY_NAME}' deleted successfully")
    
    # Optionally delete the .pem file
    import os
    pem_file = f"{KEY_NAME}.pem"
    if os.path.exists(pem_file):
        os.remove(pem_file)
        print(f"  ✅ Local key file '{pem_file}' deleted")
except Exception as e:
    if 'not found' in str(e).lower():
        print("  ℹ️  Key pair not found")
    else:
        print(f"  ⚠️  Error deleting key pair: {e}")

# ===== 6. CHECK FOR ANY LEFTOVER RESOURCES =====
print("\n📌 Step 6: Checking for leftover resources...")

# Check for any remaining instances with the template tag
print("\n  Checking for any remaining instances...")
remaining_instances = ec2.describe_instances(
    Filters=[{'Name': 'tag:Template', 'Values': [TEMPLATE_NAME]}]
)
for reservation in remaining_instances['Reservations']:
    for instance in reservation['Instances']:
        if instance['State']['Name'] != 'terminated':
            print(f"  ⚠️  Found leftover instance: {instance['InstanceId']}")
            # Terminate it
            ec2.terminate_instances(InstanceIds=[instance['InstanceId']])
            print(f"  ✅ Terminated leftover instance")

# Check for network interfaces that might be left
print("\n  Checking for orphaned network interfaces...")
try:
    nics = ec2.describe_network_interfaces(
        Filters=[
            {'Name': 'group-name', 'Values': [EC2_SG_NAME, ALB_SG_NAME]},
            {'Name': 'status', 'Values': ['available']}
        ]
    )
    for nic in nics['NetworkInterfaces']:
        print(f"  Found orphaned ENI: {nic['NetworkInterfaceId']}")
        ec2.delete_network_interface(NetworkInterfaceId=nic['NetworkInterfaceId'])
        print(f"  ✅ Deleted orphaned ENI")
except Exception as e:
    pass

# ===== 7. SUMMARY =====
print("\n" + "="*70)
print("✅ CLEANUP COMPLETED SUCCESSFULLY!")
print("="*70)
print("The following resources have been deleted:")
print(f"  • Key Pair: {KEY_NAME}")
print(f"  • EC2 Security Group: {EC2_SG_NAME}")
print(f"  • ALB Security Group: {ALB_SG_NAME}")
print(f"  • EC2 Instance(s): {INSTANCE_NAME}*")
print(f"  • Load Balancer: {ALB_NAME}")
print(f"  • Target Group: {TG_NAME}")
print("="*70)

# Optional: Verify cleanup
print("\n📋 Verifying cleanup (optional)...")
verify = input("Would you like to verify the cleanup? (yes/no): ")
if verify.lower() == 'yes':
    print("\n" + "="*70)
    print("VERIFICATION RESULTS")
    print("="*70)
    
    # Check key pair
    try:
        ec2.describe_key_pairs(KeyNames=[KEY_NAME])
        print("❌ Key pair still exists")
    except:
        print("✅ Key pair deleted")
    
    # Check security groups
    for sg_name in [EC2_SG_NAME, ALB_SG_NAME]:
        try:
            ec2.describe_security_groups(GroupNames=[sg_name])
            print(f"❌ Security group '{sg_name}' still exists")
        except:
            print(f"✅ Security group '{sg_name}' deleted")
    
    # Check instances
    instances = ec2.describe_instances(
        Filters=[{'Name': 'tag:Name', 'Values': [INSTANCE_NAME]}]
    )
    found = False
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            if instance['State']['Name'] != 'terminated':
                print(f"❌ Instance {instance['InstanceId']} still exists")
                found = True
    if not found:
        print("✅ All instances terminated")
    
    # Check ALB
    try:
        elbv2.describe_load_balancers(Names=[ALB_NAME])
        print("❌ ALB still exists")
    except:
        print("✅ ALB deleted")
    
    print("="*70)

print("\n🎉 Cleanup script finished!")
