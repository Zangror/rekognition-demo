# Generate collection 

aws rekognition create-collection --collection-id umons-demo --region eu-west-1 --profile 993176408040_AdministratorAccess
aws rekognition delete-collection --collection-id umons-demo --region eu-west-1 --profile 993176408040_AdministratorAccess

## Copy images to the bucket

aws s3 cp images s3://demostack-uploadedphotoa83329a4-igro2sjxezug --recursive

# Invoke api gateway 

curl -X POST https://e3whp7i2ri.execute-api.eu-west-1.amazonaws.com/prod/auth -d @payload/1_happy_face.json -H "Content-Type: application/json"