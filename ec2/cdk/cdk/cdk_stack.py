from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_ec2 as ec2
)
from constructs import Construct

# 从user_data.txt 文件读出 user_data
with open('user_data.txt') as f:
    user_data = f.read()

class CdkStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Find the Default VPC
        default_vpc = ec2.Vpc.from_lookup(
            self, "DefaultVpc", 
            is_default=True
        )

        # Found the latest debian 11 arm64 AMI which could be launched as t4g.small 
        # If using debian-12-arm64, it has external managed Python 3.11. Whisper installation fails.
        image = ec2.LookupMachineImage(
            owners = ['amazon'],
            name = 'debian-11-arm64*',
            filters={
                'virtualization-type': ['hvm'],
                'architecture': ['arm64']
            },
        )
        
        # Create an IAM role for SSM
        ssm_role = iam.Role(self, "SSMInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")]
        )

        # Create an instance profile and add the role to it
        ssm_profile = iam.CfnInstanceProfile(self, "SSMInstanceProfile",
            roles=[ssm_role.role_name]
        )

        # Create an security group and open a port
        sg = ec2.SecurityGroup(self, "SecurityGroup",
            vpc=default_vpc
        )
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "Allow HTTP")

        # 创建Elastic IP
        eip = ec2.CfnEIP(self, "MyEIP")

        instance = ec2.Instance(
            self, "MyInstance",
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.SMALL),
            vpc=default_vpc,
            security_group=sg,
            machine_image=image,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            user_data=ec2.UserData.custom(user_data),
            role=ssm_role
        )
        # 设置标签
        instance.instance.add_property_override(
            "Tags", [
                {
                    "Key": "environment",
                    "Value": "prod"
                },
                {
                    "Key": "Name",
                    "Value": "vox-extension-be"
                },
                {
                    "Key": "project",
                    "Value": "whisper"
                }
            ]
        )
        # 将Elastic IP关联到EC2实例
        ec2.CfnEIPAssociation(self, "EIPAssoc",
            eip=eip.ref,
            instance_id=instance.instance_id
        )