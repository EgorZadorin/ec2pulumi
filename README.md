# ec2pulumi
using pulumi to provision EC2 instances behind a load balancer 

A sample project that uses Pulumi to provision two EC2 instances behind a load balancer. The load balancer is able to direct different users to different servers. A user1 is always redirected to server1 and user2 is always redirected to server2
