from troposphere import Base64, Join, Parameter, Ref, Template, Tags, cloudwatch
from troposphere.ecs import Cluster
from troposphere.autoscaling import AutoScalingGroup, Metadata, ScalingPolicy, StepAdjustments, LaunchConfiguration,BlockDeviceMapping,EBSBlockDevice,Tag
import troposphere.ec2 as ec2
from troposphere.policies import AutoScalingReplacingUpdate, AutoScalingRollingUpdate, UpdatePolicy




def main():
    t = Template()
    t.add_version('2010-09-09')
    t.set_description("AWS CloudFormation ECS example")

    # Add the Parameters

    AMI = t.add_parameter(Parameter(
        "AMI",
        Type="String",
    ))

    ClusterSize = t.add_parameter(Parameter(
        "ClusterSize",
        Type="String",
    ))

    ClusterType = t.add_parameter(Parameter(
        "ClusterType",
        Type="String",
    ))

    InstanceType = t.add_parameter(Parameter(
        "InstanceType",
        Type="String",
    ))

    IamInstanceProfile = t.add_parameter(Parameter(
        "IamInstanceProfile",
        Type="String",
    ))

    KeyName = t.add_parameter(Parameter(
        "KeyName",
        Type="AWS::EC2::KeyPair::KeyName",
    ))

    MaxClusterSize = t.add_parameter(Parameter(
        "MaxClusterSize",
        Type="String",
    ))

    RollingUpdate = t.add_parameter(Parameter(
        "RollingUpdate",
        Type="String",
    ))

    Stage = t.add_parameter(Parameter(
        "Stage",
        Type="String",
    ))

    Subnets = t.add_parameter(Parameter(
        "Subnets",
        Type="List<AWS::EC2::Subnet::Id>",
    ))

    VpcCidr = t.add_parameter(Parameter(
        "VpcCidr",
        Type="String",
    ))

    VpcId = t.add_parameter(Parameter(
        "VpcId",
        Type="AWS::EC2::VPC::Id",
    ))



    ContainerInstances = t.add_resource(LaunchConfiguration(
        'ContainerInstances',
        UserData=Base64(Join('',
                             ['#!/bin/bash -xe\n',
                              'echo ECS_CLUSTER=',Ref('AWS::StackName'),'>> /etc/ecs/ecs.config\n',
                              'systemctl enable docker-container@ecs-agent.service\n',
                              'systemctl start docker-container@ecs-agent.service\n',
                              '/usr/bin/cfn-signal -e $? ',
                              '         --stack ',
                              Ref('AWS::StackName'),
                              '         --resource ECSAutoScalingGroup ',
                              '         --region ',
                              Ref('AWS::Region'),
                              '\n'
                              ])),
        ImageId=Ref(AMI),
        KeyName=Ref(KeyName),
        SecurityGroups=[Ref('EcsSecurityGroup')],
        IamInstanceProfile=Ref(IamInstanceProfile),
        InstanceType=Ref(InstanceType)
    ))

    ECSCluster = t.add_resource(Cluster(
        'EcsCluster',
        ClusterName=Ref('AWS::StackName')
    ))

    ECSAutoScalingGroup = t.add_resource(AutoScalingGroup(
        'ECSAutoScalingGroup',
        DesiredCapacity=Ref(ClusterSize),
        MinSize=Ref(ClusterSize),
        MaxSize=Ref(MaxClusterSize),
        VPCZoneIdentifier=Ref(Subnets),
        LaunchConfigurationName=Ref('ContainerInstances'),
        HealthCheckType="EC2",
        UpdatePolicy=UpdatePolicy(
            AutoScalingReplacingUpdate=AutoScalingReplacingUpdate(
                WillReplace=True,
            ),
            AutoScalingRollingUpdate=AutoScalingRollingUpdate(
                PauseTime='PT5M',
                MinInstancesInService=Ref(ClusterSize),
                MaxBatchSize='1',
                WaitOnResourceSignals=True
            )
        ),
        Tags=[
            Tag("Project","demo",True),
            Tag("Stage",Ref(Stage),True),
            Tag("Name","home-ecs",True),
        ]
    ))

    t.add_resource(ScalingPolicy(
        "EcsAsgScaleDown",
        AdjustmentType="PercentChangeInCapacity",
        AutoScalingGroupName=Ref("ECSAutoScalingGroup"),
        MetricAggregationType="Average",
        MinAdjustmentMagnitude="1",
        PolicyType="StepScaling",
        StepAdjustments=[
            StepAdjustments(
                MetricIntervalLowerBound="-10",
                MetricIntervalUpperBound="0",
                ScalingAdjustment="-10"
            ),
            StepAdjustments(
                MetricIntervalUpperBound="-10",
                ScalingAdjustment="-20"
            )
        ]
    )
    )

    t.add_resource(ScalingPolicy(
        'EcsScaleUp',
        AdjustmentType="PercentChangeInCapacity",
        AutoScalingGroupName=Ref("ECSAutoScalingGroup"),
        EstimatedInstanceWarmup="300",
        MetricAggregationType="Average",
        MinAdjustmentMagnitude="1",
        PolicyType="StepScaling",
        StepAdjustments=[
            StepAdjustments(
                MetricIntervalLowerBound="0",
                MetricIntervalUpperBound="10",
                ScalingAdjustment="10"
            ),
            StepAdjustments(
                MetricIntervalLowerBound="10",
                ScalingAdjustment="20"
            )
        ]
    )
    )

    t.add_resource(cloudwatch.Alarm(
        "EcsScaleDownAlarm",
        ActionsEnabled="True",
        MetricName="CPUUtilization",
        AlarmActions=[Ref("EcsAsgScaleDown")],
        AlarmDescription="Scale down ECS Instances",
        Namespace="AWS/EC2",
        Statistic="Average",
        Period="60",
        EvaluationPeriods="6",
        Threshold="25",
        ComparisonOperator="LessThanThreshold",
        Dimensions=[
            cloudwatch.MetricDimension(Name="AutoScalingGroupName", Value=Ref("ECSAutoScalingGroup"))
        ]
    )
    )

    t.add_resource(cloudwatch.Alarm(
        "EcsAsgScaleUpAlarm",
        ActionsEnabled="True",
        MetricName="CPUUtilization",
        AlarmActions=[Ref("EcsScaleUp")],
        AlarmDescription="Scale up ECS Instances",
        Namespace="AWS/EC2",
        Statistic="Average",
        Period="60",
        EvaluationPeriods="3",
        Threshold="65",
        ComparisonOperator="GreaterThanThreshold",
        Dimensions=[
            cloudwatch.MetricDimension(Name="AutoScalingGroupName", Value=Ref("ECSAutoScalingGroup"))
        ]
    )
    )

    EC2SecurityGroup = t.add_resource(ec2.SecurityGroup(
        'EcsSecurityGroup',
        GroupDescription='ECS InstanceSecurityGroup',
        SecurityGroupIngress=[
            ec2.SecurityGroupRule(
                IpProtocol='tcp',
                FromPort='22',
                ToPort='22',
                CidrIp='0.0.0.0/0'
            ),
            ec2.SecurityGroupRule(
                IpProtocol='tcp',
                FromPort='31000',
                ToPort='61000',
                CidrIp='0.0.0.0/0'
            )
        ],
        VpcId=Ref(VpcId)
    ))


    with open("ecs-ec2-cluster-cf.yaml", "w") as yamlout:
        yamlout.write(t.to_yaml())

if __name__ == '__main__':
    main()