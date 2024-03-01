# t4g.small instances powered by AWS Graviton2 processors 

Free Trial: Try Amazon EC2 t4g.small instances powered by AWS Graviton2 processors free for up to 750 hours / month until Dec 31st 2024. 
All existing and new customers with an AWS account can take advantage of the T4g free trial. The T4g free trial is available for a limited time until December 31, 2024. The T4g free trial will be available in addition to the existing AWS Free Tier on t2.micro/t3.micro. Customers who have exhausted their t2.micro (or t3.micro, depending on the Region) Free Tier usage can still benefit from the T4g free trial.


Refer to https://aws.amazon.com/blogs/aws/new-t4g-instances-burstable-performance-powered-by-aws-graviton2/ and https://aws.amazon.com/ec2/faqs/#t4g-instances


Found the latest debian 12 arm64 AMI which could be launched as t4g.small
```bash
LATEST_AMI_NAME=$(aws ec2 describe-images --owners amazon \
    --filters "Name=name,Values=debian-12-arm64*" "Name=virtualization-type,Values=hvm" "Name=architecture,Values=arm64" \
    --query 'sort_by(Images, &CreationDate)[-1].[ImageId]' \
    --output text)
aws ec2 describe-images --image-ids $LATEST_AMI_NAME
```

Create a userData file to initialize the instance with your necessary tools
```bash
cat <<EOF > user_data.txt
#!/bin/bash

# Basics
sudo apt update
sudo apt upgrade -y
sudo apt-get -qy install --no-install-recommends curl wget zip unzip pv jqs

# SSM Agent #
wget https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/debian_arm64/amazon-ssm-agent.deb
sudo dpkg -i amazon-ssm-agent.deb
sudo systemctl status amazon-ssm-agent
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent

# AWS CLI v2 and Git #
sudo apt install git -y
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Python3
sudo apt-get install python3-pip -y
pip install boto3
EOF
```
Create a IAM policy, role and Ec2 instance profile with SSM session manager permission to assign to the new instance
```bash
aws iam create-role --role-name "SSMInstanceRole" --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name "SSMInstanceRole" \
  --policy-arn "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
aws iam create-instance-profile \
  --instance-profile-name SSMInstanceProfile
aws iam add-role-to-instance-profile \
  --instance-profile-name SSMInstanceProfile \
  --role-name SSMInstanceRole
```
If you prefer to use existing role and Ec2 instance profile:
```bash
aws iam list-entities-for-policy --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
aws iam list-instance-profiles-for-role --role-name <RoleName you picked from output of above cmd>
```
Find and use a subnet within a VPC
```bash
# find all VPCs and chose one, etc. the first one
aws ec2 describe-vpcs --query "Vpcs[].VpcId"
VPC=$(aws ec2 describe-vpcs --query "Vpcs[?].VpcId" --output text) # repalce ? with the index of your choice
# find all subnets, private subnets and choose one. Private one is better, but not necessary.
aws ec2 describe-subnets \
  --query "Subnets[?VpcId==\`$VPC\`].SubnetId"
aws ec2 describe-subnets \
  --query "Subnets[?VpcId==\`$VPC\`] | [?MapPublicIpOnLaunch==\`false\`].SubnetId"
SN=$(aws ec2 describe-subnets \
  --query "Subnets[?VpcId==\`$VPC\`].SubnetId | [0]" \
  --output text)

# Create an EC2 instance which we can use SSM session manager to remote into it
aws ec2 run-instances --image-id $LATEST_AMI_NAME \
  --count 1 --instance-type t4g.small \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=vma-test-2-delete}]' \
  --iam-instance-profile Name=SSMInstanceProfile \
  --key-name vma_rsa \
  --subnet-id $SN \
  --user-data file://user_data.txt
```
## Test using aws cli and ssh

Assume you have aws cli and session manager plugin installed already.
```bash
aws ssm --profile ${AWS_PROFILE} --region ${region}  start-session --target ${InstanceId}
```
Linux: use SSH on top of Session manager
```bash
$ tail -4 ~/.ssh/config 
# SSH over Session Manager
host i-* mi-*
  ProxyCommand sh -c "aws ssm --profile dec --region us-east-1 start-session --target %h --document-name AWS-StartSSHSession --parameters 'portNumber=%p'"
  IdentityFile ~/.ssh/vma_rsa
$ ssh admin@i-0fdc88fe37f8af01b
```