# aws-ecs-examples
cloudformation script examples for ecs

- These files are build with troposhere: https://github.com/cloudtools/troposphere

ecs-ec2.py : to build an ECS cluster and create an ASG for EC2 infrastucture.

ecs-ec2-service.py : to build a service on ECS-EC2 infrastructure. It will create a task-defintion, LB and CNAME.

ecs-fargate-service.py : to build a service on ECS-fargate infrastructure. It will create a task-defintion, LB and CNAME.
