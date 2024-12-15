from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import boto3
from django.conf import settings
from .models import CustomUser

class CognitoJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        # Check if the token has "Bearer" and extract the actual token
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            raise AuthenticationFailed('Authorization header must start with Bearer')

        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)

        try:
            # Verify token with AWS Cognito
            response = client.get_user(AccessToken=token)
            user_email = response['UserAttributes'][0]['Value']  # Assuming email is the first attribute
            user, created = CustomUser.objects.get_or_create(email=user_email)
            return (user, None)
        except client.exceptions.NotAuthorizedException:
            raise AuthenticationFailed('Invalid token or expired token')
        except client.exceptions.InvalidParameterException as e:
            raise AuthenticationFailed(f'Invalid token format: {str(e)}')
        except client.exceptions.UserNotFoundException:
            raise AuthenticationFailed('User not found')
        except Exception as e:
            raise AuthenticationFailed(f'Error during authentication: {str(e)}')
