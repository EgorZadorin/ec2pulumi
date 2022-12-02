"""An AWS Python Pulumi program"""

import pulumi
import pulumi_aws as aws

ami = aws.ec2.get_ami(
    most_recent=True,
    owners=["amazon"],
    filters=[{"name": "description", "values": ["Amazon Linux 2 *"]}],
)

vpc = aws.ec2.get_vpc(default=True)
vpc_subnets = aws.ec2.get_subnet_ids(vpc_id=vpc.id)

group = aws.ec2.SecurityGroup(
    "web-secgrp",
    description="Enable HTTP Access",
    vpc_id=vpc.id,
    ingress=[
        {
          "protocol": "tcp",
          "from_port": 22,
          "to_port": 22,
          "cidr_blocks": ["0.0.0.0/0"],
        },
        {
            "protocol": "icmp",
            "from_port": 8,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],
        },
        {
            "protocol": "tcp",
            "from_port": 80,
            "to_port": 80,
            "cidr_blocks": ["0.0.0.0/0"],
        },
    ],
    egress=[
        {
            "protocol": "-1",
            "from_port": 0,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],
        }
    ],
)

lb = aws.lb.LoadBalancer(
    "loadbalancer",
    internal=False,
    security_groups=[group.id],
    subnets=vpc_subnets.ids,
    load_balancer_type="application",
)

target_groups = [
    aws.lb.TargetGroup("target-group1", port=80, protocol="HTTP", target_type="ip", vpc_id=vpc.id),
    aws.lb.TargetGroup("target-group2", port=80, protocol="HTTP", target_type="ip", vpc_id=vpc.id),
]

ips = []
hostnames = []

listener = aws.lb.Listener(
    "listener",
    load_balancer_arn=lb.arn,
    port=80,
    default_actions=[{"type": "forward", "target_group_arn": target_groups[0].arn}],
)

for i in [1, 2]:
    listener_rule = aws.lb.ListenerRule(f"static{i}",
        listener_arn=listener.arn,
        priority=i,
        actions=[aws.lb.ListenerRuleActionArgs(
            type="forward",
            target_group_arn=target_groups[i - 1].arn,
        )],
        conditions=[aws.lb.ListenerRuleConditionArgs(
            path_pattern=aws.lb.ListenerRuleConditionPathPatternArgs(
               values=[f"/{i}/*"],
            ),
        ),
    ])

    server = aws.ec2.Instance(
        f"web-server-{i}",
        instance_type="t2.micro",
        vpc_security_group_ids=[group.id],
        ami=ami.id,
        user_data="""#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd
echo "<h1>Hello World from server {}</h1>" > /var/www/html/index.html
sudo chmod 777 /var/www/html -R
mkdir /var/www/html/{}
echo "<h1>This is directory in server {}!</h1>" > /var/www/html/{}/index.html
""".format(
            i,
            i,
            i,
            i
        ),
        tags={
            "Name": "web-server",
        },
    )
    ips.append(server.public_ip)
    hostnames.append(server.public_dns)

    attachment = aws.lb.TargetGroupAttachment(
        f"web-server-{i}",
        target_group_arn=target_groups[i - 1].arn,
        target_id=server.private_ip,
        port=80,
    )

pulumi.export("ips", ips)
pulumi.export("hostnames", hostnames)
pulumi.export("url", lb.dns_name)
