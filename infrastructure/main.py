from typing import Dict, Text

import monocdk as core

from monocdk import (
    aws_s3,
    aws_dynamodb,
    aws_lambda,
    aws_iam,
    aws_stepfunctions,
    aws_stepfunctions_tasks,
    aws_apigateway,
)

from infrastructure.utils import (
    Stack,
    build_path_to_lambdas,
    python_38_function_bundling_options,
)


class DemoStack(Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        collection = "umons-demo"

        # Bucket where photo are uploaded
        uploaded_photo_bucket = aws_s3.Bucket(
            self,
            "uploaded-photo",
            removal_policy=core.RemovalPolicy.DESTROY,
        )
        thumbnail_photo_bucket = aws_s3.Bucket(
            self,
            "thumbnail-photo",
            removal_policy=core.RemovalPolicy.DESTROY,
        )

        # DynamoDB to store metadata of photo
        metadata_table = aws_dynamodb.Table(
            self,
            "metadata",
            partition_key=aws_dynamodb.Attribute(
                name="user_id", type=aws_dynamodb.AttributeType.STRING
            ),
            billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=core.RemovalPolicy.DESTROY,
        )

        # Create all the lambda
        rekognition_code = aws_lambda.Code.from_asset(
            path=build_path_to_lambdas("rekognition"),
            bundling=python_38_function_bundling_options,
        )
        thumbnail_code = aws_lambda.Code.from_asset(
            path=build_path_to_lambdas("thumbnail"),
            bundling=python_38_function_bundling_options,
        )

        face_detection_function = aws_lambda.Function(
            self,
            "FaceDetection",
            code=rekognition_code,
            handler="face_detection.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_8,
        )
        uploaded_photo_bucket.grant_read(face_detection_function)
        face_detection_function.add_to_role_policy(
            statement=aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=["rekognition:DetectFaces"],
                resources=["*"],
            )
        )

        face_index_function = aws_lambda.Function(
            self,
            "FaceIndex",
            code=rekognition_code,
            handler="face_index.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            environment={"REKOGNITION_COLLECTION_ID": collection},
        )
        uploaded_photo_bucket.grant_read(face_index_function)
        face_index_function.add_to_role_policy(
            statement=aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=["rekognition:IndexFaces"],
                resources=[
                    f"arn:aws:rekognition:{self.region}:{self.account}:collection/{collection}"
                ],
            )
        )

        face_search_function = aws_lambda.Function(
            self,
            "FaceSearch",
            code=rekognition_code,
            handler="face_search.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            environment={"REKOGNITION_COLLECTION_ID": collection},
        )
        uploaded_photo_bucket.grant_read(face_search_function)
        face_search_function.add_to_role_policy(
            statement=aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=["rekognition:SearchFacesByImage"],
                resources=[
                    f"arn:aws:rekognition:{self.region}:{self.account}:collection/{collection}"
                ],
            )
        )

        thumbnail_create_function = aws_lambda.Function(
            self,
            "ThumbnailCreate",
            code=thumbnail_code,
            handler="create.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            environment={"BUCKET": thumbnail_photo_bucket.bucket_name},
            timeout=core.Duration.minutes(amount=1),
        )
        uploaded_photo_bucket.grant_read(thumbnail_create_function)
        thumbnail_photo_bucket.grant_write(thumbnail_create_function)

        # Create the step function tasks
        failed = aws_stepfunctions.Pass(
            self,
            "Failed",
            parameters={
                "Error": aws_stepfunctions.JsonPath.string_at("$.ErrorInfo.Error"),
                "Cause": aws_stepfunctions.JsonPath.string_at(
                    "$.ErrorInfo.Cause.errorMessage"
                ),
            },
            result_path="$",
        )
        error = aws_stepfunctions.Pass(
            self,
            "Error",
            parameters={
                "Error": aws_stepfunctions.JsonPath.string_at("$.ErrorInfo.Error"),
                "Cause.$": "States.StringToJson($.ErrorInfo.Cause)",
            },
            result_path="$.ErrorInfo",
        )
        error.next(failed)

        face_detection_task = aws_stepfunctions_tasks.LambdaInvoke(
            self,
            "Detect Face",
            lambda_function=face_detection_function,
            payload=aws_stepfunctions.TaskInput.from_object(
                {
                    "bucket": aws_stepfunctions.JsonPath.string_at(
                        "$.parameters.bucket"
                    ),
                    "key": aws_stepfunctions.JsonPath.string_at("$.parameters.key"),
                }
            ),
            payload_response_only=True,
            result_path="$.FaceDetection",
        )
        face_detection_task.add_catch(
            errors=["PhotoDoesNotMeetRequirementError"],
            result_path="$.ErrorInfo",
            handler=error,
        )

        face_index_task = aws_stepfunctions_tasks.LambdaInvoke(
            self,
            "Face index",
            lambda_function=face_index_function,
            payload=aws_stepfunctions.TaskInput.from_object(
                {
                    "bucket": aws_stepfunctions.JsonPath.string_at(
                        "$.parameters.bucket"
                    ),
                    "key": aws_stepfunctions.JsonPath.string_at("$.parameters.key"),
                    "user_id": aws_stepfunctions.JsonPath.string_at(
                        "$.parameters.user_id"
                    ),
                }
            ),
            payload_response_only=True,
            result_path="$.FaceIndex",
        )

        face_search_task = aws_stepfunctions_tasks.LambdaInvoke(
            self,
            "Search Face",
            lambda_function=face_search_function,
            payload=aws_stepfunctions.TaskInput.from_object(
                {
                    "bucket": aws_stepfunctions.JsonPath.string_at(
                        "$.parameters.bucket"
                    ),
                    "key": aws_stepfunctions.JsonPath.string_at("$.parameters.key"),
                }
            ),
            payload_response_only=True,
            result_path="$.FaceSearch",
        )

        thumbnail_create_task = aws_stepfunctions_tasks.LambdaInvoke(
            self,
            "Create thumbnail",
            lambda_function=thumbnail_create_function,
            payload=aws_stepfunctions.TaskInput.from_object(
                {
                    "bucket": aws_stepfunctions.JsonPath.string_at(
                        "$.parameters.bucket"
                    ),
                    "key": aws_stepfunctions.JsonPath.string_at("$.parameters.key"),
                }
            ),
            payload_response_only=True,
            result_path="$.ThumbnailCreate",
        )
        persist_metadata_task = aws_stepfunctions_tasks.DynamoPutItem(
            self,
            "Persist metadata",
            table=metadata_table,
            item={
                "user_id": aws_stepfunctions_tasks.DynamoAttributeValue.from_string(
                    aws_stepfunctions.JsonPath.string_at("$.parameters.user_id")
                ),
                "photo": aws_stepfunctions_tasks.DynamoAttributeValue.from_map(
                    {
                        "bucket": aws_stepfunctions_tasks.DynamoAttributeValue.from_string(
                            aws_stepfunctions.JsonPath.string_at("$.parameters.bucket")
                        ),
                        "key": aws_stepfunctions_tasks.DynamoAttributeValue.from_string(
                            aws_stepfunctions.JsonPath.string_at("$.parameters.key")
                        ),
                    }
                ),
                "thumbnail": aws_stepfunctions_tasks.DynamoAttributeValue.from_map(
                    {
                        "bucket": aws_stepfunctions_tasks.DynamoAttributeValue.from_string(
                            aws_stepfunctions.JsonPath.string_at(
                                "$.ThumbnailCreate.bucket"
                            )
                        ),
                        "key": aws_stepfunctions_tasks.DynamoAttributeValue.from_string(
                            aws_stepfunctions.JsonPath.string_at(
                                "$.ThumbnailCreate.key"
                            )
                        ),
                    },
                ),
            },
            result_path="$.PersistMetadataTask",
        )
        retrieve_metadata_task = aws_stepfunctions_tasks.DynamoGetItem(
            self,
            "Retrieve metadata",
            table=metadata_table,
            key={
                "user_id": aws_stepfunctions_tasks.DynamoAttributeValue.from_string(
                    aws_stepfunctions.JsonPath.string_at("$.parameters.user_id")
                ),
            },
            output_path="$",
        )

        user_created = aws_stepfunctions.Pass(
            self,
            "UserCreated",
            parameters={
                "UserId": aws_stepfunctions.JsonPath.string_at("$.parameters.user_id"),
                "Thumbnail": {
                    "Bucket": aws_stepfunctions.JsonPath.string_at(
                        "$.ThumbnailCreate.bucket"
                    ),
                    "Key": aws_stepfunctions.JsonPath.string_at(
                        "$.ThumbnailCreate.key"
                    ),
                },
            },
            result_path="$",
        )
        user_retrieved = aws_stepfunctions.Pass(
            self,
            "User retrieved",
            parameters={
                "UserId": aws_stepfunctions.JsonPath.string_at("$.Item.user_id.S"),
                "Thumbnail": {
                    "Bucket": aws_stepfunctions.JsonPath.string_at(
                        "$.Item.thumbnail.M.bucket.S"
                    ),
                    "Key": aws_stepfunctions.JsonPath.string_at(
                        "$.Item.thumbnail.M.key.S"
                    ),
                },
            },
            result_path="$",
        )

        not_same_user = aws_stepfunctions.Pass(
            self,
            "User is not the same as he said !",
            result_path="$.ErrorInfo",
            result=aws_stepfunctions.Result.from_object(
                {
                    "Error": "IdentificationError",
                    "Cause": {"errorMessage": "User are not the same."},
                }
            ),
        )
        choice_check_existence = (
            aws_stepfunctions.Choice(
                self,
                "Check if user already exist",
            )
            .when(
                condition=aws_stepfunctions.Condition.boolean_equals(
                    variable="$.FaceSearch.exists", value=True
                ),
                next=aws_stepfunctions.Choice(self, "CheckUserIdIsTheSame")
                .when(
                    condition=aws_stepfunctions.Condition.string_equals_json_path(
                        variable="$.FaceSearch.user_id", value="$.parameters.user_id"
                    ),
                    next=retrieve_metadata_task.next(user_retrieved),
                )
                .otherwise(not_same_user.next(failed)),
            )
            .otherwise(
                face_index_task.next(thumbnail_create_task)
                .next(persist_metadata_task)
                .next(user_created)
            )
        )

        # Create the step function definition
        definition = face_detection_task.next(face_search_task).next(
            choice_check_existence
        )

        step_function = aws_stepfunctions.StateMachine(
            scope=self,
            id="StateFunction",
            definition=definition,
            tracing_enabled=True,
            state_machine_type=aws_stepfunctions.StateMachineType.EXPRESS,
        )

        # Expose one API Gateway
        api_gw_sfn_role = aws_iam.Role(
            self,
            "sfnStartExecutionRole",
            assumed_by=aws_iam.ServicePrincipal("apigateway.amazonaws.com"),
        )
        step_function.grant_execution(
            api_gw_sfn_role, "states:StartExecution", "states:StartSyncExecution"
        )
        step_function.grant_start_execution(api_gw_sfn_role)

        api = aws_apigateway.RestApi(self, "RestAPI")
        auth = api.root.add_resource("auth")
        auth.add_method(
            http_method="POST",
            integration=aws_apigateway.AwsIntegration(
                service="states",
                action="StartSyncExecution",
                integration_http_method="POST",
                options=aws_apigateway.IntegrationOptions(
                    credentials_role=api_gw_sfn_role,
                    integration_responses=[
                        aws_apigateway.IntegrationResponse(status_code="200")
                    ],
                    request_templates={
                        "application/json": f"""{{
                        "input": "$util.escapeJavaScript($input.body)",
                        "stateMachineArn": "{step_function.state_machine_arn}"
                    }}"""
                    },
                ),
            ),
            method_responses=[aws_apigateway.MethodResponse(status_code="200")],
        )
