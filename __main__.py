import pulumi
import pulumi_aws as aws

size = 't2.micro'

ami = aws.get_ami(most_recent=True,
                  owners=["137112412989"],
                  filters=[aws.GetAmiFilterArgs(name="name", values=["amzn-ami-hvm-*"])])

group = aws.ec2.SecurityGroup('web-secgrp',
    description='Enable HTTP access',
    ingress=[aws.ec2.SecurityGroupIngressArgs(
        protocol='tcp',
        from_port=80,
        to_port=80,
        cidr_blocks=['0.0.0.0/0'],
    )])

user_data1 = """
#!/bin/bash
echo "server1" > index.html
nohup python -m SimpleHTTPServer 80 &
"""

user_data2 = """
#!/bin/bash
echo "server2" > index.html
nohup python -m SimpleHTTPServer 80 &
"""

server1 = aws.ec2.Instance('web-server1-www',
    instance_type=size,
    vpc_security_group_ids=[group.id],
    user_data=user_data1,
    ami=ami.id)

server2 = aws.ec2.Instance('web-server2-www',
    instance_type=size,
    vpc_security_group_ids=[group.id],
    user_data=user_data2,
    ami=ami.id)

pulumi.export('server1', server1.public_dns)
pulumi.export('server2', server2.public_dns)