# Converted from ELBSample.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import Base64, FindInMap, GetAtt, Join, Output
from troposphere import Parameter, Ref, Template
import troposphere.ec2 as ec2
import troposphere.elasticloadbalancingv2 as elb
from troposphere.route53 import RecordSetType
import troposphere.ecs as ecs


from troposphere.ecs import Cluster, Service, TaskDefinition,ContainerDefinition, NetworkConfiguration,AwsvpcConfiguration,Environment,Secret, PortMapping





def main():
    template = Template()
    template.add_version("2010-09-09")

    template.set_description(
        "AWS CloudFormation ECS Service")

    # Add the Parameters

    Application = template.add_parameter(Parameter(
        "Application",
        Type="String",
    ))


    DockerImage = template.add_parameter(Parameter(
        "DockerImage",
        Type="String",
    ))

    USERNAME = template.add_parameter(Parameter(
        "USERNAME",
        Type="String",
    ))

    ClusterName = template.add_parameter(Parameter(
        "ClusterName",
        Type="String",
    ))

    ContainerPort = template.add_parameter(Parameter(
        "ContainerPort",
        Type="String",
    ))

    HostPort = template.add_parameter(Parameter(
        "HostPort",
        Type="String",
    ))

    HostedZoneName = template.add_parameter(Parameter(
        "HostedZoneName",
        Type="String",
    ))

    CertArn = template.add_parameter(Parameter(
        "CertArn",
        Type="String",
    ))

    ExecutionRoleArn = template.add_parameter(Parameter(
        "ExecutionRoleArn",
        Type="String",
        Description="Execution Role to get creadentials from ssm"
    ))

    HealthCheckPath = template.add_parameter(Parameter(
        "HealthCheckPath",
        Type="String",
    ))

    HealthCheckIntervalSeconds = template.add_parameter(Parameter(
        "HealthCheckIntervalSeconds",
        Type="String",
    ))

    HealthyThresholdCount = template.add_parameter(Parameter(
        "HealthyThresholdCount",
        Type="String",
    ))

    HealthCheckTimeoutSeconds = template.add_parameter(Parameter(
        "HealthCheckTimeoutSeconds",
        Type="String",
    ))

    UnhealthyThresholdCount = template.add_parameter(Parameter(
        "UnhealthyThresholdCount",
        Type="String",
    ))

    VpcId = template.add_parameter(Parameter(
        "VpcId",
        Type="String",
    ))

    Subnets = template.add_parameter(Parameter(
        "Subnets",
        Type="List<AWS::EC2::Subnet::Id>",
    ))


    # Add the application ELB

    NetworkLB = template.add_resource(elb.LoadBalancer(
        "NetworkLB",
        Name=Join("",[Ref(Application),"-nlb"]),
        Scheme="internet-facing",
        Subnets=Ref(Subnets),
        Type='network'
    ))

    NlbTargetGroup = template.add_resource(elb.TargetGroup(
        "NlbTargetGroup",
        Name='ecs-service-targetgroup',
        HealthCheckIntervalSeconds=Ref(HealthCheckIntervalSeconds),
        HealthCheckProtocol="TCP",
        HealthyThresholdCount=Ref(HealthyThresholdCount),
        Port=80,
        Protocol="TCP",
        UnhealthyThresholdCount=Ref(UnhealthyThresholdCount),
        VpcId=Ref(VpcId)
    ))


    NlbListener = template.add_resource(elb.Listener(
        "Listener",
        DependsOn=["NlbTargetGroup","NetworkLB"],
        Certificates=[elb.Certificate(
            CertificateArn=Ref(CertArn)
        )],
        Port="443",
        Protocol="TLS",
        LoadBalancerArn=Ref(NetworkLB),
        DefaultActions=[elb.Action(
            Type="forward",
            TargetGroupArn=Ref(NlbTargetGroup)
        )]
    ))



    Task_Definition = template.add_resource(TaskDefinition(
        'TaskDefinition',
        Memory='500',
        ExecutionRoleArn=Ref(ExecutionRoleArn),
        ContainerDefinitions=[
            ContainerDefinition(
                Name=Join("",[Ref(Application)]),
                Image=Ref(DockerImage),
                Essential=True,
                Secrets=[
                    Secret(
                        Name='USERNAME',
                        ValueFrom=Ref(USERNAME)
                    )],
                Environment=[
                    Environment(
                        Name="DOCKER_LABELS",
                        Value="true"
                    )
                ],
                DockerLabels={
                    'aws-account' : Ref("AWS::AccountId"),
                    'region': Ref("AWS::Region"),
                    'stack': Ref("AWS::StackName")
                },
                PortMappings=[PortMapping(
                    ContainerPort=Ref(ContainerPort),
                    HostPort=Ref(HostPort)
                )]
            )
        ]
    ))


    app_service = template.add_resource(Service(
        "AppService",
        DependsOn=["Listener","TaskDefinition"],
        Cluster=Ref(ClusterName),
        DesiredCount=1,
        TaskDefinition=Ref(Task_Definition),
        ServiceName=Join("",[Ref(Application),"-ecs-service"]),
        LoadBalancers=[ecs.LoadBalancer(
            ContainerName=Join("",[Ref(Application)]),
            ContainerPort=Ref(ContainerPort),
            TargetGroupArn=Ref(NlbTargetGroup)
        )]

    ))

    AppDNSRecord = template.add_resource(RecordSetType(
        "AppDNSRecord",
        DependsOn=["AppService"],
        HostedZoneName=Join("", [Ref(HostedZoneName), "."]),
        Name=Join("",[Ref(Application), ".", Ref(HostedZoneName), "."]),
        Type="CNAME",
        TTL="900",
        ResourceRecords=[GetAtt(NetworkLB,"DNSName")]
    ))

    template.add_output(Output(
        "URL",
        Description="DomainName",
        Value=Join("",["https://",Ref(AppDNSRecord)])
    ))


    with open("ecs-ec2-service-cf.yaml", "w") as yamlout:
        yamlout.write(template.to_yaml())

if __name__ == '__main__':
    main()