import boto3
import os
import time
from botocore.exceptions import ClientError

def create_unique_bucket(s3_client, region='us-east-1'):
    """Create a globally unique bucket."""
    bucket_name = f"botopython-{int(time.time())}-{os.getlogin()}"
    try:
        if region == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        print(f"✅ Bucket '{bucket_name}' created successfully in {region}.")
        return bucket_name
    except ClientError as e:
        print(f"❌ Error creating bucket: {e}")
        exit(1)

def upload_file_to_s3(s3_client, file_path, bucket_name, object_name=None):
    """Upload a file to S3."""
    if not object_name:
        object_name = os.path.basename(file_path)

    if not os.path.exists(file_path):
        print(f"❌ File '{file_path}' does not exist.")
        exit(1)

    try:
        s3_client.upload_file(file_path, bucket_name, object_name)
        print(f"✅ File '{file_path}' uploaded as '{object_name}' in bucket '{bucket_name}'.")
    except ClientError as e:
        print(f"❌ Error uploading file: {e}")
        exit(1)

def main():
    s3 = boto3.client('s3')
    region = 'us-east-1'

    #  Create a unique bucket
    bucket_name = create_unique_bucket(s3, region)

    #  List local files (optional, nice for logging)
    print("\n📁 Local files in current directory:")
    for f in os.listdir('.'):
        print("-", f)

    # Upload sample file
    file_to_upload = '../data/sample.txt'  # relative path from scripts folder
    upload_file_to_s3(s3, file_to_upload, bucket_name)

if __name__ == "__main__":
    main()

