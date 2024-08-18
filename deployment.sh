#!/bin/bash -ex

# Synopsis of bash file:
	# •	Foundation Stack Deployment: The script first deploys a foundational CloudFormation stack using a template (00_foundation.yaml), which likely sets up basic infrastructure, including an S3 bucket.
	# •	Retrieve S3 Bucket Name: After deployment, it retrieves the name of the S3 bucket created by the foundation stack.
	# •	Prepare API Code: The script then prepares the API for deployment by installing dependencies.
	# •	Package API: The API code and dependencies are packaged and uploaded to the S3 bucket.
	# •	API Stack Deployment: Finally, the script deploys the API stack using the generated template that references the uploaded artifacts.

# Deploying foundation

aws cloudformation deploy \
    --template-file cloudformations/00_foundation.yaml \
    --stack-name foundation \
    --tags name=foundation

# Getting the GeneralBucketName 

GeneralBucketName=$(aws cloudformation describe-stacks \
    --stack-name foundation \
    --query 'Stacks[0].Outputs[?OutputKey==`GeneralBucketName`].OutputValue' \
    --output text)

# Deploying the API

cfndir=$PWD
cd api
pip install -r requirements.txt -t .
cd $cfndir


aws cloudformation package \
    --template-file cloudformations/01_api.yaml \
    --s3-bucket $GeneralBucketName \
    --s3-prefix infrastructure/api \
    --output-template-file cloudformations/01_api_generated.yaml \


# TODO: Upload to bucket. 

aws cloudformation deploy \
    --template-file cloudformations/01_api_generated.yaml \
    --stack-name listtracker-api \
    --capabilities CAPABILITY_IAM \
    --capabilities CAPABILITY_NAMED_IAM
