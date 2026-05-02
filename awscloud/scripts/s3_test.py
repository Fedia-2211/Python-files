import boto3

s3 = boto3.client('s3')

# List all buckets
response = s3.list_buckets()
print("Buckets in your account:")
for b in response['Buckets']:
    print("-", b['Name'])
