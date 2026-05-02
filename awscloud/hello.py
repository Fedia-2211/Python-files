

import boto3
import os
from botocore.exceptions import ClientError

# --- Configuration ---
bucket_name = 'botopython34072340'
file_to_upload = 'solorsysten.txt'
s3_object_name = 'solorsysten.ext'  # How the file will be named in S3

# --- Initialize S3 client ---
s3 = boto3.client('s3')

# --- 1. Create bucket (if it doesn't exist) ---
try:
    s3.head_bucket(Bucket=bucket_name)
    print(f"Bucket '{bucket_name}' already exists.")
except ClientError:
    # Bucket does not exist, create it
    region = 'us-east-1'  # Change to your desired AWS region
    try:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': region}
        )
        print(f"Bucket '{bucket_name}' created successfully in region {region}.")
    except ClientError as e:
        print(f"Error creating bucket: {e}")
        exit(1)

# --- 2. List current directory (optional) ---
print("Current directory contents:")
os.system("ls")  # or os.listdir('.') for cross-platform

# --- 3. Upload file ---
try:
    s3.upload_file(file_to_upload, bucket_name, s3_object_name)
    print(f"File '{file_to_upload}' uploaded to bucket '{bucket_name}' as '{s3_object_name}'.")
except ClientError as e:
    print(f"Error uploading file: {e}")
    exit(1)
