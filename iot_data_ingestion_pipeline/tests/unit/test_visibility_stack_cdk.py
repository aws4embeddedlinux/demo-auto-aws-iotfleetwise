import aws_cdk as core
import aws_cdk.assertions as assertions
from iot_data_ingestion_pipeline.visibility_stack import VisibilityStack
import json

#app and stack definition
database_name = "visibility"
table_name = "visibility"
def app_stack_assertions():
    app = core.App()
    f=open("tests/unit/accountConfig.json", "r")
    accountData= json.load(f)
    stack = VisibilityStack(app, "visibility",
                            env=core.Environment(
        account=accountData["account"],
        region=accountData["region"]))
    template = assertions.Template.from_stack(stack)
    return app, stack, template

def test_timestream_db_created():
    app, stack, template= app_stack_assertions()
    template.has_resource_properties("AWS::Timestream::Database", {
        "DatabaseName": database_name,
    })

def test_timestream_table_created():
    app, stack, template= app_stack_assertions()
    template.has_resource_properties("AWS::Timestream::Table", {
        "DatabaseName": database_name,
        "TableName": table_name, 
        "RetentionProperties": {"MemoryStoreRetentionPeriodInHours": 96,
        "MagneticStoreRetentionPeriodInDays": 1500 }
    })

def test_IoT_rule_created_CANData_to_Timestream():
    app, stack, template= app_stack_assertions()
    template.has_resource_properties("AWS::IoT::TopicRule", {
        "TopicRulePayload" : {
            "Actions" : [{"Timestream": {"DatabaseName":database_name, "TableName":table_name}}],
            "AwsIotSqlVersion": "2015-10-08"
        },
        "RuleName": "CANData_to_Timestream", 
    })


def test_IoT_rule_created_FreeRTOSOS_to_Timestream():
    app, stack, template= app_stack_assertions()

    template.has_resource_properties("AWS::IoT::TopicRule", {
        "TopicRulePayload" : {
            "Actions" : [{"Timestream": {"DatabaseName":database_name, "TableName":table_name}}],
            "AwsIotSqlVersion": "2016-03-23"
        },
        "RuleName": "FreeRTOSOS_to_Timestream", 
    })

def test_IoT_rule_created_FreeRTOSApp_to_Timestream():
    app, stack, template= app_stack_assertions()

    template.has_resource_properties("AWS::IoT::TopicRule", {
        "TopicRulePayload" : {
            "Actions" : [{"Timestream": {"DatabaseName":database_name, "TableName":table_name}}],
            "AwsIotSqlVersion": "2016-03-23"
        },
        "RuleName": "FreeRTOSApp_to_Timestream", 
    })

def test_IoT_rule_created_Nucleus_to_Timestream():
    app, stack, template= app_stack_assertions()

    template.has_resource_properties("AWS::IoT::TopicRule", {
        "TopicRulePayload" : {
            "Actions" : [{"Timestream": {"DatabaseName":database_name, "TableName":table_name}}],
            "AwsIotSqlVersion": "2016-03-23"
        },
        "RuleName": "ggTelemetry_to_Timestream", 
    })

def test_IoT_rule_created_ggProcessing_to_Timestream():
    app, stack, template= app_stack_assertions()

    template.has_resource_properties("AWS::IoT::TopicRule", {
        "TopicRulePayload" : {
            "Actions" : [{"Timestream": {"DatabaseName":database_name, "TableName":table_name}}],
            "AwsIotSqlVersion": "2016-03-23"
        },
        "RuleName": "ggProcessing_to_Timestream", 
    })

def test_timestream_role_creation():
    app, stack, template= app_stack_assertions()

    template.has_resource_properties("AWS::IAM::Role", {
        "AssumeRolePolicyDocument": {
            "Statement": [{"Principal": {"Service": "iot.amazonaws.com"}}]
        },
        "ManagedPolicyArns": [{ "Fn::Join": ["", ["arn:",
              { "Ref": "AWS::Partition" },
              ":iam::aws:policy/AmazonTimestreamFullAccess"]] }],
         "RoleName": "timestream_access_role"
    })

def test_grafana_execution_role_creation():
    app, stack, template= app_stack_assertions()

    template.has_resource_properties("AWS::IAM::Role", {
        "AssumeRolePolicyDocument": {
            "Statement": [{"Principal": {"Service": "ecs-tasks.amazonaws.com"}}]
        }
    })


def test_ECS_definition():
    app, stack, template= app_stack_assertions()

    template.has_resource_properties("AWS::ECS::TaskDefinition", 
                                    {
                                    "Cpu": "256",
                                    "ExecutionRoleArn": { "Fn::GetAtt": [ "GrafanaexecutionRole0137FD77", "Arn" ] },
                                    "Memory": "512",
                                    "NetworkMode": "awsvpc",
                                    "RequiresCompatibilities": [ "FARGATE" ],
                                    "TaskRoleArn": { "Fn::GetAtt": [ "GrafanataskRole9665A38A", "Arn" ] } 
    })
