import boto3
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model

User = get_user_model()

class SyncCognitoMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            user = request.user
            if user.cognito_sub:
                client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
                try:
                    response = client.admin_get_user(
                        UserPoolId=settings.AWS_COGNITO_USER_POOL_ID,
                        Username=user.email
                    )
                    # Update user attributes from Cognito to Django
                    for attribute in response['UserAttributes']:
                        if attribute['Name'] == 'email_verified':
                            user.email_verified = attribute['Value'] == 'true'
                    user.save()
                except client.exceptions.UserNotFoundException:
                    pass
