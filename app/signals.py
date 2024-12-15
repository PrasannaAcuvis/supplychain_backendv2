from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import CustomUser
import boto3
from django.conf import settings

@receiver(post_delete, sender=CustomUser)
def delete_user_in_cognito(sender, instance, **kwargs):
    """
    Deletes the user from AWS Cognito when they are deleted in Django.
    """
    client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
    try:
        client.admin_delete_user(
            UserPoolId=settings.AWS_COGNITO_USER_POOL_ID,
            Username=instance.email
        )
    except client.exceptions.UserNotFoundException:
        pass  # User was already deleted in Cognito
