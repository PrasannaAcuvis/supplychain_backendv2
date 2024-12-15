from datetime import datetime
from django.utils import timezone
from rest_framework import generics, mixins, status
from rest_framework.response import Response
from .models import *
from .serializers import *
import requests
import logging
from rest_framework.response import Response
from rest_framework.views import APIView
import boto3
from django.conf import settings
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django import forms
from django.http import HttpResponse
import csv, io
from django.db.models import Count,Sum, Case, When, FloatField, IntegerField
from django.http import Http404
from rest_framework.filters import SearchFilter, OrderingFilter
# from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from rest_framework import filters
from rest_framework.permissions import IsAuthenticated


logger = logging.getLogger(__name__)

class BestMatchAPIView(generics.GenericAPIView,
                       mixins.ListModelMixin,
                       mixins.CreateModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.DestroyModelMixin):
    queryset = BestMatch.objects.all()
    serializer_class = BestMatchSerializer
    lookup_field = 'pk'

    # External API URL and Authorization
    API_URL = "https://app.2050-materials.com/developer/api/get_best_match/"
    API_HEADERS = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM0MzU0MDA0LCJpYXQiOjE3MzQyNjc2MDQsImp0aSI6IjYwODFmYjUzMzM4MjQ1OTQ5OWQ5ZTQ4N2Q1ODZlMzQ3IiwidXNlcl9pZCI6NjYzMX0.zMfotIBdyMdTQIGiD-Zceu_RlKowUlauEVSYNPiOAtM"
    }

    def convert_date_format(self, date_str):
        """Convert date from DD/MM/YYYY to YYYY-MM-DD format."""
        try:
            return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid date format: {date_str}")
            return None

    def process_unprocessed_records(self):
        unprocessed_records = BestMatch.objects.filter(processed=False)
        logger.info(f"Found {unprocessed_records.count()} unprocessed records")

        for record in unprocessed_records:
            if record.delivery_note_date:
                # Convert delivery_note_date to string before passing to convert_date_format
                converted_date = self.convert_date_format(record.delivery_note_date.strftime("%d/%m/%Y"))
                if converted_date:
                    record.delivery_note_date = converted_date
                else:
                    logger.error(f"Skipping record ID {record.id} due to invalid date format.")
                    continue

            api_payload = {
                "input_items": [record.product_description],
                "include_product_data": True,
                "include_material_data": True
            }

            try:
                response = requests.post(self.API_URL, json=api_payload, headers=self.API_HEADERS)
                logger.info(f"API response status code: {response.status_code}")

                if response.status_code == 200:
                    api_data = response.json()
                    product_info = api_data.get("results", {}).get(record.product_description, {})
                    material_facts = api_data.get("product_data", {}).get(record.product_description, {}).get("material_facts", {})
                    scaling_factors = material_facts.get("scaling_factors", {})

                    record.product_name = product_info.get("product_name")
                    record.material_name = product_info.get("material_name")
                    record.product_company_name = product_info.get("product_company_name")
                    record.product_match_score = product_info.get("product_match_score")
                    record.global_warming_potential_fossil = material_facts.get("global_warming_potential_fossil", {}).get("A1A2A3")
                    record.declared_unit = material_facts.get("declared_unit")
                    record.scaling_factor = scaling_factors.get(record.unit_of_measure, {}).get("value")
                    record.data_source = material_facts.get("data_source")
                    record.processed = True
                    record.processed_timestamp = timezone.now()

                    # Calculate kgco2_per_m2 and assign it to kgco2
                    if record.global_warming_potential_fossil and record.scaling_factor and record.quantity:
                        kgco2_per_m2 = (float(record.global_warming_potential_fossil) / float(record.scaling_factor)) * (float(record.quantity) / 5000)
                        record.kgco2 = kgco2_per_m2

                    record.save()
                    logger.info(f"Record with ID {record.id} has been updated and saved.")

                    # Fetch Phase instance
                    try:
                        phase_instance = Phase.objects.get(pk=record.phase_id) if record.phase_id else None
                    except Phase.DoesNotExist:
                        phase_instance = None
                        logger.error(f"Phase with ID {record.phase_id} does not exist for record ID {record.id}")

                    # Copy data to InvoiceData model
                    InvoiceData.objects.create(
                        delivery_note_ref_no=record.delivery_note_ref_no,
                        supplier_name=record.product_company_name,
                        data_source=record.data_source,
                        product_description=record.product_description,
                        material_name=record.material_name,
                        entry_time=record.entry_time.date() if record.entry_time else timezone.now().date(),
                        quantity=record.quantity,
                        unit_of_measure=record.unit_of_measure,
                        phase_name=phase_instance,  # Assign the Phase instance
                        kgco2=record.kgco2
                    )

                    logger.info(f"Data copied to InvoiceData for record ID {record.id}")

                else:
                    logger.error(f"API request failed for record ID {record.id}: {response.status_code} - {response.text}")

            except requests.RequestException as e:
                logger.error(f"RequestException for record ID {record.id}: {e}")

    def get(self, request, pk=None):
        self.process_unprocessed_records()
        if pk:
            return self.retrieve(request, pk)
        return self.list(request)

    def post(self, request):
        self.process_unprocessed_records()
        return Response({"message": "All unprocessed records have been processed."}, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        return self.update(request, pk)

    def delete(self, request, pk=None):
        return self.destroy(request, pk)

class FileUploadForm(forms.Form):
    file = forms.FileField()


class CSVUploadView(FormView):
    template_name = 'app/upload_invoice.html'
    form_class = FileUploadForm
    success_url = reverse_lazy('upload_csv')  # Redirect after successful POST

    def form_valid(self, form):
        csv_file = form.cleaned_data['file']
        if not csv_file.name.endswith('.csv'):
            return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

        data_set = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        next(io_string)  # Skip the header row

        for row in csv.reader(io_string, delimiter=',', quotechar='"'):
            try:
                # Parse the date with mm/dd/yyyy format
                date_added = datetime.strptime(row[6], '%m/%d/%Y').date()

                # Retrieve or create the Phase instance
                phase_instance, _ = Phase.objects.get_or_create(name=row[13])

                # Create the InvoiceData instance
                InvoiceData.objects.create(
                    customer_ref=int(row[0]) if row[0] else None,
                    delivery_note_ref_no=int(row[1]) if row[1] else None,
                    supplier_name=row[2],
                    data_source=row[3],
                    product_description=row[4],
                    material_name=row[5],
                    entry_time=date_added,
                    quantity=int(row[7]) if row[7] else None,
                    unit_of_measure=row[8],
                    country_name=row[9],
                    region_name=row[10],
                    city_name=row[11],
                    building_name=row[12],
                    phase_name=phase_instance,
                    kgco2=int(row[14]) if row[14] else None,
                )
            except (ValueError, IndexError) as e:
                return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

        return super().form_valid(form)
    


logger = logging.getLogger(__name__)

class CustomSearchFilter(filters.SearchFilter):
    def get_search_terms(self, request):
        """
        Override get_search_terms to split the query into individual keywords
        based on commas and strip spaces.
        """
        params = request.query_params.get(self.search_param, '')
        terms = [param.strip() for param in params.split(',') if param.strip()]
        logger.debug(f"Search terms: {terms}")
        return terms

    def filter_queryset(self, request, queryset, view):
        search_terms = self.get_search_terms(request)
        if not search_terms:
            return queryset

        # Prepare queries for each term across all specified search fields
        combined_queries = Q()
        for search_term in search_terms:
            # Initialize a query for each term
            query = Q()
            for search_field in self.get_search_fields(view, request):
                # Construct query for each field using 'icontains' for case-insensitive partial matches
                condition = {f"{search_field}__icontains": search_term}
                query |= Q(**condition)
            combined_queries |= query  # Use OR to combine queries for different terms
            logger.debug(f"Building query for term '{search_term}': {query}")

        final_queryset = queryset.filter(combined_queries)
        logger.debug(f"Final queryset count: {final_queryset.count()}")
        return final_queryset





class InvoiceDataView(generics.ListAPIView):
    # queryset = InvoiceData.objects.all()
    queryset = InvoiceData.objects.select_related('phase_name').all()
    serializer_class = InvoiceDataSerializer
    filter_backends = (CustomSearchFilter, OrderingFilter)
    search_fields = ('country_name', 'region_name', 'city_name', 'building_name', 'supplier_name','phase_name__name', 'data_source', 'entry_time', 'product_description', 'material_name')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Aggregate overall totals
        aggregate_data = queryset.aggregate(
            total_kgco2=Sum('kgco2')
        )

        # Aggregate totals by material name (corrected)
        material_name_aggregates = queryset.values('material_name').annotate(
            total_kgco2=Sum('kgco2')
        ).order_by('material_name')

        # Aggregate carbon and kgco2 based on the status of 'Estimate' and 'Actual'
        carbon_status_sums = queryset.aggregate(
            estimate_kgco2=Sum(Case(
                When(data_source='EPD', then='kgco2'),
                output_field=IntegerField(),
            )),
            actual_kgco2=Sum(Case(
                When(data_source='Average', then='kgco2'),
                output_field=IntegerField(),
            )),
        )

        # Calculate percentages if total_kgco2 is not zero
        total_kgco2 = aggregate_data['total_kgco2'] or 0  # Avoid division by zero
        if total_kgco2 > 0:
            estimate_percentage = (carbon_status_sums['estimate_kgco2'] or 0) / total_kgco2 * 100
            actual_percentage = (carbon_status_sums['actual_kgco2'] or 0) / total_kgco2 * 100
        else:
            estimate_percentage = 0
            actual_percentage = 0

        # Aggregate by region
        region_aggregates = queryset.values('region_name').annotate(
            total_kgco2=Sum('kgco2')
        ).order_by('region_name')

        # Aggregate by city
        city_aggregates = queryset.values('city_name').annotate(
            total_kgco2=Sum('kgco2')
        ).order_by('city_name')

        # Aggregate by building name
        building_aggregates = queryset.values('building_name').annotate(
            total_kgco2=Sum('kgco2')
        ).order_by('building_name')

        # Nested aggregation structure
        nested_structure = []
        for region in queryset.values('region_name').distinct():
            region_queryset = queryset.filter(region_name=region['region_name'])
            region_total = region_queryset.aggregate(
                total_kgco2=Sum('kgco2')
            )
            
            cities_data = []
            for city in region_queryset.values('city_name').distinct():
                city_queryset = region_queryset.filter(city_name=city['city_name'])
                city_total = city_queryset.aggregate(
                    total_kgco2=Sum('kgco2')
                )
                
                buildings_data = []
                for building in city_queryset.values('building_name').distinct():
                    building_queryset = city_queryset.filter(building_name=building['building_name'])
                    building_total = building_queryset.aggregate(
                        total_kgco2=Sum('kgco2')
                    )
                    
                    phases_data = building_queryset.values('phase_name__name').annotate(
                        total_kgco2=Sum('kgco2')
                    ).order_by('phase_name__name')
                    
                    buildings_data.append({
                        'building_name': building['building_name'],
                        'total_kgco2': building_total['total_kgco2'],
                        'phases': list(phases_data)
                    })
                
                cities_data.append({
                    'city_name': city['city_name'],
                    'total_kgco2': city_total['total_kgco2'],
                    'buildings': buildings_data
                })
            
            nested_structure.append({
                'region_name': region['region_name'],
                'total_kgco2': region_total['total_kgco2'],
                'cities': cities_data
            })

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'overall_aggregates': aggregate_data,
            'material_name_aggregates': list(material_name_aggregates),
            'carbon_status_totals': {
                'estimate': {
                    'total_kgco2': carbon_status_sums['estimate_kgco2'] or 0
                },
                'actual': {
                    'total_kgco2': carbon_status_sums['actual_kgco2'] or 0
                }
            },
            'carbon_status_percentage': {
                'EPD': estimate_percentage,
                'average': actual_percentage,
            },
            'region_aggregates': list(region_aggregates),
            'city_aggregates': list(city_aggregates),
            'building_aggregates': list(building_aggregates),
            'nested_structure': nested_structure  # Nested structure by region, city, building, and phases
        })
    


# Country CRUD Views
class CountryListCreateAPI(generics.ListCreateAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]

class CountryRetrieveUpdateDestroyAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]

# Region CRUD Views
class RegionListCreateAPI(generics.ListCreateAPIView):
    serializer_class = RegionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Region.objects.all()
        country_id = self.request.query_params.get('country_id')
        if country_id is not None:
            queryset = queryset.filter(country_id=country_id)
        return queryset

class RegionRetrieveUpdateDestroyAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [IsAuthenticated]

# City CRUD Views
class CityListCreateAPI(generics.ListCreateAPIView):
    serializer_class = CitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = City.objects.all()
        region_id = self.request.query_params.get('region_id')
        if region_id is not None:
            queryset = queryset.filter(region_id=region_id)
        return queryset

class CityRetrieveUpdateDestroyAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = [IsAuthenticated]

# Building CRUD Views
class BuildingListCreateAPI(generics.ListCreateAPIView):
    serializer_class = BuildingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Building.objects.all()
        city_id = self.request.query_params.get('city_id')
        if city_id is not None:
            queryset = queryset.filter(city_id=city_id)
        return queryset

class BuildingRetrieveUpdateDestroyAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer
    permission_classes = [IsAuthenticated]

# User Signup (Create Only)
class UserSignUpAPI(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
        
        try:
            response = client.sign_up(
                ClientId=settings.AWS_COGNITO_APP_CLIENT_ID,
                Username=user.email,  # Using email as the username
                Password=serializer.validated_data['password'],
                UserAttributes=[
                    {'Name': 'email', 'Value': user.email}
                    # Remove email_verified here, as Cognito will handle verification
                ]
            )
            user.cognito_sub = response['UserSub']
            user.save()
        except client.exceptions.UsernameExistsException:
            raise ValueError("Email already exists in Cognito")
        
#User Details api
class UserDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'id'  # Use 'id' as the primary key for lookup

    def get_object(self):
        user = super().get_object()
        # Optionally sync with Cognito if needed
        self.sync_with_cognito(user)
        return user

    def sync_with_cognito(self, user):
        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
        try:
            response = client.admin_get_user(
                UserPoolId=settings.AWS_COGNITO_USER_POOL_ID,
                Username=user.email
            )
            # Update user attributes from Cognito to Django if necessary
            for attribute in response['UserAttributes']:
                if attribute['Name'] == 'email_verified':
                    user.email_verified = attribute['Value'] == 'true'
            user.save()
        except client.exceptions.UserNotFoundException:
            pass

    def perform_update(self, serializer):
        user = serializer.save()
        self.update_cognito_user(user)

    def update_cognito_user(self, user):
        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
        attributes = [
            {'Name': 'email', 'Value': user.email},
            {'Name': 'email_verified', 'Value': 'true' if user.email_verified else 'false'}
        ]
        try:
            client.admin_update_user_attributes(
                UserPoolId=settings.AWS_COGNITO_USER_POOL_ID,
                Username=user.email,
                UserAttributes=attributes
            )
        except client.exceptions.UserNotFoundException:
            raise ValueError("User not found in Cognito")

    def perform_destroy(self, instance):
        self.delete_cognito_user(instance)
        super().perform_destroy(instance)

    def delete_cognito_user(self, user):
        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
        try:
            client.admin_delete_user(
                UserPoolId=settings.AWS_COGNITO_USER_POOL_ID,
                Username=user.email
            )
        except client.exceptions.UserNotFoundException:
            pass



# Verify Email API
class VerifyEmailAPI(APIView):
    serializer_class = VerifyEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
        try:
            # Confirm the user's email verification in Cognito
            client.confirm_sign_up(
                ClientId=settings.AWS_COGNITO_APP_CLIENT_ID,
                Username=email,
                ConfirmationCode=otp
            )

            # Update email_verified field in Django's database
            user = CustomUser.objects.filter(email=email).first()
            if user:
                user.email_verified = True
                user.save()

            return Response({"message": "Email verified successfully"}, status=status.HTTP_200_OK)

        except client.exceptions.CodeMismatchException:
            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
        except client.exceptions.UserNotFoundException:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        
class ResendConfirmationCodeAPI(generics.CreateAPIView):
    """
    Resend the confirmation code to the user's email if they haven't verified their email.
    """
    serializer_class = ResendCodeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
        
        try:
            # Resend confirmation code via Cognito
            client.resend_confirmation_code(
                ClientId=settings.AWS_COGNITO_APP_CLIENT_ID,
                Username=email
            )
            return Response({"message": "Confirmation code resent successfully"}, status=status.HTTP_200_OK)

        except client.exceptions.UserNotFoundException:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except client.exceptions.InvalidParameterException as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        



# Login API view
class LoginAPI(generics.CreateAPIView):
    """
    Authenticate the user using AWS Cognito and return tokens if successful.
    """
    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)

        try:
            # Authenticate the user using AWS Cognito
            response = client.initiate_auth(
                ClientId=settings.AWS_COGNITO_APP_CLIENT_ID,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password
                }
            )
            # Return tokens if authentication is successful
            return Response({
                "message": "Login successful",
                "access_token": response['AuthenticationResult']['AccessToken'],
                "id_token": response['AuthenticationResult']['IdToken'],
                "refresh_token": response['AuthenticationResult']['RefreshToken']
            }, status=status.HTTP_200_OK)

        except client.exceptions.NotAuthorizedException:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        except client.exceptions.UserNotFoundException:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class ListUsersAPI(APIView):
    """
    Retrieve a list of all users in the AWS Cognito User Pool,
    with additional fields from Django database.
    """
    def get(self, request, *args, **kwargs):
        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
        try:
            # Use list_users to fetch all users in the user pool
            response = client.list_users(
                UserPoolId=settings.AWS_COGNITO_USER_POOL_ID,
                Limit=60  # Adjust the limit if needed
            )
            
            users = []
            for user in response['Users']:
                email = next((attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'email'), None)
                email_verified = any(attr['Value'] == 'true' for attr in user['Attributes'] if attr['Name'] == 'email_verified')
                
                # Retrieve additional fields from Django database if they exist
                try:
                    custom_user = CustomUser.objects.get(email=email)
                    user_data = {
                        'id': custom_user.id,
                        'email': email,
                        
                        'email_verified': email_verified
                    }
                except CustomUser.DoesNotExist:
                    # If user details don't exist in Django, default values
                    user_data = {
                        'id': None,
                        'email': email,
                        'email_verified': email_verified
                    }
                
                users.append(user_data)
            
            serializer = UserListSerializer(users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except client.exceptions.ResourceNotFoundException:
            return Response({"error": "User pool not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

# class FileUploadForm(forms.Form):
#     file = forms.FileField()

# class CSVUploadView(FormView):
#     template_name = 'app/upload_invoice.html'
#     form_class = FileUploadForm
#     success_url = reverse_lazy('upload_csv')  # Redirect after POST

#     def form_valid(self, form):
#         csv_file = form.cleaned_data['file']
#         if not csv_file.name.endswith('.csv'):
#             return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

#         data_set = csv_file.read().decode('UTF-8')
#         io_string = io.StringIO(data_set)
#         next(io_string)  # Skip header row
#         for row in csv.reader(io_string, delimiter=',', quotechar='"'):
#             try:
#                 date_added = datetime.strptime(row[4], '%m/%d/%Y').date()  # Assume Date is still at the 4th index
#                 InvoiceData.objects.create(
#                     supplier_name=row[0],
#                     carbon=row[1],
#                     material_description=row[2],
#                     material_type=row[3],
#                     date=date_added,
#                     quantity=row[5],
#                     unit_measure=row[6],
#                     #cost=row[7],
#                     country=row[7],
#                     region=row[8],
#                     city=row[9],
#                     #site_name=row[11],
#                     building_name=row[10],
#                     element_group=row[11],
#                     gia=row[12],
#                     carbon_co2=row[13],
#                     kgco2=row[14],
#                 )
#             except ValueError as e:
#                 return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

#         return super().form_valid(form)
#########################################################################

class CSVUploadViewDesign(FormView):
    template_name = 'app/upload_design.html'
    form_class = FileUploadForm
    success_url = reverse_lazy('upload_design')  # Redirect after POST

    def form_valid(self, form):
        csv_file = form.cleaned_data['file']
        if not csv_file.name.endswith('.csv'):
            return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

        data_set = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        next(io_string)  # Skip header row
        for row in csv.reader(io_string, delimiter=',', quotechar='"'):
            try:
                DesignData.objects.create(
                    region=row[0],
                    city=row[1],
                    building_name=row[2],
                    substructure=row[3],
                    superstructure=row[4],
                    façade=row[5],
                    internal_walls_partitions=row[6],
                    internal_finishes=row[7],
                    ff_fe=row[8],
                    gia=row[9],
                    
                )
            except ValueError as e:
                return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

        return super().form_valid(form)


class CSVUploadViewYourMaterial(FormView):
    template_name = 'app/upload_your_material.html'
    form_class = FileUploadForm
    success_url = reverse_lazy('upload_your_material')  # Redirect after POST

    def form_valid(self, form):
        csv_file = form.cleaned_data['file']
        if not csv_file.name.endswith('.csv'):
            return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

        data_set = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        next(io_string)  # Skip header row
        for row in csv.reader(io_string, delimiter=',', quotechar='"'):
            try:
                # Ensure row has at least one column
                if len(row) < 1:
                    continue  # Skip empty rows

                YourMaterial.objects.create(
                    name=row[0],
                )
            except IndexError:
                return HttpResponse("CSV format error: Missing required data in some rows.", status=400)
            except ValueError as e:
                return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

        return super().form_valid(form)


class CSVUploadViewYourMaterialEmission(FormView):
    template_name = 'app/upload_your_material_emission.html'
    form_class = FileUploadForm
    success_url = reverse_lazy('upload_your_material_emission')  # Redirect after POST

    def form_valid(self, form):
        csv_file = form.cleaned_data['file']
        if not csv_file.name.endswith('.csv'):
            return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

        data_set = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        next(io_string)  # Skip header row
        for row in csv.reader(io_string, delimiter=',', quotechar='"'):
            try:
                name_id=int(row[1])
                country_instance=YourMaterial.objects.get(pk=name_id)
                # date_added = datetime.strptime(row[4], '%m/%d/%Y').date()  # Assume Date is still at the 4th index
                YourMaterialEmission.objects.create(
                    emission=row[0],
                    name=country_instance
                )
            except ValueError as e:
                return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

        return super().form_valid(form)

class CSVUploadViewEcoMaterial(FormView):
    template_name = 'app/upload_eco_material.html'
    form_class = FileUploadForm
    success_url = reverse_lazy('upload_eco_material')  # Redirect after POST

    def form_valid(self, form):
        csv_file = form.cleaned_data['file']
        if not csv_file.name.endswith('.csv'):
            return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

        data_set = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        next(io_string)  # Skip header row
        for row in csv.reader(io_string, delimiter=',', quotechar='"'):
            try:
                # date_added = datetime.strptime(row[4], '%m/%d/%Y').date()  # Assume Date is still at the 4th index
                EcoMaterial.objects.create(
                    name=row[0],
                )
            except ValueError as e:
                return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

        return super().form_valid(form)


class CSVUploadViewEcoMaterialEmission(FormView):
    template_name = 'app/upload_eco_material_emission.html'
    form_class = FileUploadForm
    success_url = reverse_lazy('upload_eco_material_emission')  # Redirect after POST

    def form_valid(self, form):
        csv_file = form.cleaned_data['file']
        if not csv_file.name.endswith('.csv'):
            return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

        data_set = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        next(io_string)  # Skip header row
        for row in csv.reader(io_string, delimiter=',', quotechar='"'):
            try:
                name_id=int(row[1])
                country_instance=EcoMaterial.objects.get(pk=name_id)
                # date_added = datetime.strptime(row[4], '%m/%d/%Y').date()  # Assume Date is still at the 4th index
                EcoMaterialEmission.objects.create(
                    emission=row[0],
                    name=country_instance
                )
            except ValueError as e:
                return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

        return super().form_valid(form)

class CSVUploadViewCompareCarbon(FormView):
    template_name = 'app/upload_compare_carbon.html'
    form_class = FileUploadForm
    success_url = reverse_lazy('upload_compare_carbon')  # Redirect after POST

    def form_valid(self, form):
        csv_file = form.cleaned_data['file']
        if not csv_file.name.endswith('.csv'):
            return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

        data_set = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        next(io_string)  # Skip header row
        for row in csv.reader(io_string, delimiter=',', quotechar='"'):
            try:
                name_id=int(row[1])
                country_instance=Country.objects.get(pk=name_id)
                # date_added = datetime.strptime(row[4], '%m/%d/%Y').date()  # Assume Date is still at the 4th index
                CompareCarbon.objects.create(
                    emission=row[0],
                    name=country_instance
                )
            except ValueError as e:
                return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

        return super().form_valid(form)
    

class CSVUploadViewCountry(FormView):
    template_name = 'app/upload_country.html'
    form_class = FileUploadForm
    success_url = reverse_lazy('upload_country')  # Redirect after POST

    def form_valid(self, form):
        csv_file = form.cleaned_data['file']
        if not csv_file.name.endswith('.csv'):
            return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

        data_set = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        next(io_string)  # Skip header row
        for row in csv.reader(io_string, delimiter=',', quotechar='"'):
            if len(row) < 1:
                return HttpResponse("Invalid CSV format.", status=400)
            try:
                Country.objects.create(name=row[0])
            except ValueError as e:
                return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

        return super().form_valid(form)


class CSVUploadViewRegion(FormView):
    template_name = 'app/upload_region.html'
    form_class = FileUploadForm
    success_url = reverse_lazy('upload_region')  # Redirect after POST

    def form_valid(self, form):
        csv_file = form.cleaned_data['file']
        if not csv_file.name.endswith('.csv'):
            return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

        try:
            data_set = csv_file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            next(io_string)  # Skip header row

            for row in csv.reader(io_string, delimiter=',', quotechar='"'):
                # Skip empty rows
                if len(row) < 2:  # Adjust based on the number of expected columns
                    continue

                try:
                    country_id = int(row[1])
                    country_instance = Country.objects.get(pk=country_id)

                    Region.objects.create(
                        name=row[0],
                        country=country_instance
                    )
                except Country.DoesNotExist:
                    return HttpResponse(f"Country with ID {row[1]} does not exist.", status=400)
                except ValueError as e:
                    return HttpResponse(f"Error parsing row: {str(e)}", status=400)

        except Exception as e:
            return HttpResponse(f"An error occurred while processing the CSV file: {str(e)}", status=400)

        return super().form_valid(form)


# class CSVUploadViewRegion(FormView):
#     template_name = 'app/upload_region.html'
#     form_class = FileUploadForm
#     success_url = reverse_lazy('upload_region')  # Redirect after POST

#     def form_valid(self, form):
#         csv_file = form.cleaned_data['file']
#         if not csv_file.name.endswith('.csv'):
#             return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

#         data_set = csv_file.read().decode('UTF-8')
#         io_string = io.StringIO(data_set)
#         next(io_string)  # Skip header row
#         for row in csv.reader(io_string, delimiter=',', quotechar='"'):
#             try:
#                 country_id=int(row[1])
#                 country_instance=Country.objects.get(pk=country_id)
#                 # date_added = datetime.strptime(row[4], '%m/%d/%Y').date()  # Assume Date is still at the 4th index
#                 Region.objects.create(
#                     name=row[0],
#                     country=country_instance
#                 )
#             except ValueError as e:
#                 return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

#         return super().form_valid(form)
    
class CSVUploadViewCity(FormView):
    template_name = 'app/upload_city.html'
    form_class = FileUploadForm
    success_url = reverse_lazy('upload_city')  # Redirect after POST

    def form_valid(self, form):
        csv_file = form.cleaned_data['file']
        if not csv_file.name.endswith('.csv'):
            return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

        data_set = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        next(io_string)  # Skip header row
        for row in csv.reader(io_string, delimiter=',', quotechar='"'):
            try:
                region_id=int(row[1])
                region_instance=Region.objects.get(pk=region_id)
                # date_added = datetime.strptime(row[4], '%m/%d/%Y').date()  # Assume Date is still at the 4th index
                City.objects.create(
                    name=row[0],
                    region=region_instance
                )
            except ValueError as e:
                return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

        return super().form_valid(form)

class CSVUploadViewBuilding(FormView):
    template_name = 'app/upload_building.html'
    form_class = FileUploadForm
    success_url = reverse_lazy('upload_building')

    def form_valid(self, form):
        csv_file = form.cleaned_data['file']
        if not csv_file.name.endswith('.csv'):
            return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

        try:
            data_set = csv_file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            next(io_string)  # Skip header row

            for row in csv.reader(io_string, delimiter=',', quotechar='"'):
                if len(row) < 2:  # Skip malformed rows
                    continue

                try:
                    city_id = int(row[1])  # City ID from the second column
                    city_instance = City.objects.get(pk=city_id)
                    Building.objects.create(
                        name=row[0],  # Building name from the first column
                        city=city_instance
                    )
                except City.DoesNotExist:
                    return HttpResponse(f"City with ID {row[1]} does not exist.", status=400)
                except ValueError as e:
                    return HttpResponse(f"Error parsing row: {str(e)}", status=400)

        except Exception as e:
            return HttpResponse(f"An error occurred while processing the CSV file: {str(e)}", status=400)

        return super().form_valid(form)


# class CSVUploadViewBuilding(FormView):
#     template_name = 'app/upload_building.html'
#     form_class = FileUploadForm
#     success_url = reverse_lazy('upload_building')  # Redirect after POST

#     def form_valid(self, form):
#         csv_file = form.cleaned_data['file']
#         if not csv_file.name.endswith('.csv'):
#             return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

#         data_set = csv_file.read().decode('UTF-8')
#         io_string = io.StringIO(data_set)
#         next(io_string)  # Skip header row
#         for row in csv.reader(io_string, delimiter=',', quotechar='"'):
#             try:
#                 region_id=int(row[1])
#                 region_instance=Region.objects.get(pk=region_id)
#                 # date_added = datetime.strptime(row[4], '%m/%d/%Y').date()  # Assume Date is still at the 4th index
#                 Building.objects.create(
#                     name=row[0],
#                     region=region_instance
#                 )
#             except ValueError as e:
#                 return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

#         return super().form_valid(form)



    

# logger = logging.getLogger(__name__)

# class CustomSearchFilter(filters.SearchFilter):
#     def get_search_terms(self, request):
#         """
#         Override get_search_terms to split the query into individual keywords
#         based on commas and strip spaces.
#         """
#         params = request.query_params.get(self.search_param, '')
#         terms = [param.strip() for param in params.split(',') if param.strip()]
#         logger.debug(f"Search terms: {terms}")
#         return terms

#     def filter_queryset(self, request, queryset, view):
#         search_terms = self.get_search_terms(request)
#         if not search_terms:
#             return queryset

#         # Prepare queries for each term across all specified search fields
#         combined_queries = Q()
#         for search_term in search_terms:
#             # Initialize a query for each term
#             query = Q()
#             for search_field in self.get_search_fields(view, request):
#                 # Construct query for each field using 'icontains' for case-insensitive partial matches
#                 condition = {f"{search_field}__icontains": search_term}
#                 query |= Q(**condition)
#             combined_queries |= query  # Use OR to combine queries for different terms
#             logger.debug(f"Building query for term '{search_term}': {query}")

#         final_queryset = queryset.filter(combined_queries)
#         logger.debug(f"Final queryset count: {final_queryset.count()}")
#         return final_queryset

# #http://52.4.52.14:8000/api/search/?search=Estimate
# #http://52.4.52.14:8000/api/search/?search=London
# class InvoiceDataView(generics.ListAPIView):
#     queryset = InvoiceData.objects.all()
#     serializer_class = InvoiceDataSerializer
#     filter_backends = (CustomSearchFilter, OrderingFilter)
#     search_fields = ('country', 'region', 'city', 'building_name', 'supplier_name', 
#                      'element_group', 'carbon', 'date', 'material_description', 'material_type')

#     def list(self, request, *args, **kwargs):
#         queryset = self.filter_queryset(self.get_queryset())

#         # Aggregate overall totals
#         aggregate_data = queryset.aggregate(
#             total_carbon=Sum('carbon_co2'),
#             total_kgco2=Sum('kgco2')
#         )

#         # Aggregate totals by material type
#         material_type_aggregates = queryset.values('material_type').annotate(
#             total_carbon=Sum('carbon_co2'),
#             total_kgco2=Sum('kgco2')
#         ).order_by('material_type')

#         # Aggregate carbon and kgco2 based on the status of 'Estimate' and 'Actual'
#         carbon_status_sums = queryset.aggregate(
#             estimate_carbon=Sum(Case(
#                 When(carbon='Estimate', then='carbon_co2'),
#                 output_field=IntegerField(),
#             )),
#             actual_carbon=Sum(Case(
#                 When(carbon='Actual', then='carbon_co2'),
#                 output_field=IntegerField(),
#             )),
#             estimate_kgco2=Sum(Case(
#                 When(carbon='Estimate', then='kgco2'),
#                 output_field=IntegerField(),
#             )),
#             actual_kgco2=Sum(Case(
#                 When(carbon='Actual', then='kgco2'),
#                 output_field=IntegerField(),
#             )),
#         )

#         # Calculate percentages if total_carbon is not zero
#         total_carbon = aggregate_data['total_carbon'] or 0  # Avoid division by zero
#         if total_carbon > 0:
#             estimate_percentage = (carbon_status_sums['estimate_carbon'] or 0) / total_carbon * 100
#             actual_percentage = (carbon_status_sums['actual_carbon'] or 0) / total_carbon * 100
#         else:
#             estimate_percentage = 0
#             actual_percentage = 0

#         # Aggregate by region
#         region_aggregates = queryset.values('region').annotate(
#             total_carbon_co2=Sum('carbon_co2'),
#             total_kgco2=Sum('kgco2')
#         ).order_by('region')

#         # Aggregate by city
#         city_aggregates = queryset.values('city').annotate(
#             total_carbon_co2=Sum('carbon_co2'),
#             total_kgco2=Sum('kgco2')
#         ).order_by('city')

#         # Aggregate by building_name
#         building_aggregates = queryset.values('building_name').annotate(
#             total_carbon_co2=Sum('carbon_co2'),
#             total_kgco2=Sum('kgco2')
#         ).order_by('building_name')

#         # Aggregate by region
#         phase_aggregates = queryset.values('element_group').annotate(
#             total_carbon_co2=Sum('carbon_co2'),
#             total_kgco2=Sum('kgco2')
#         ).order_by('element_group')

#         # Nested aggregation structure
#         nested_structure = []
#         for region in queryset.values('region').distinct():
#             region_queryset = queryset.filter(region=region['region'])
#             region_total = region_queryset.aggregate(
#                 total_carbon_co2=Sum('carbon_co2'),
#                 total_kgco2=Sum('kgco2')
#             )
            
#             cities_data = []
#             for city in region_queryset.values('city').distinct():
#                 city_queryset = region_queryset.filter(city=city['city'])
#                 city_total = city_queryset.aggregate(
#                     total_carbon_co2=Sum('carbon_co2'),
#                     total_kgco2=Sum('kgco2')
#                 )
                
#                 buildings_data = []
#                 for building in city_queryset.values('building_name').distinct():
#                     building_queryset = city_queryset.filter(building_name=building['building_name'])
#                     building_total = building_queryset.aggregate(
#                         total_carbon_co2=Sum('carbon_co2'),
#                         total_kgco2=Sum('kgco2')
#                     )
                    
#                     phases_data = building_queryset.values('element_group').annotate(
#                         total_carbon_co2=Sum('carbon_co2'),
#                         total_kgco2=Sum('kgco2')
#                     ).order_by('element_group')
                    
#                     buildings_data.append({
#                         'building_name': building['building_name'],
#                         'total_carbon_co2': building_total['total_carbon_co2'],
#                         'total_kgco2': building_total['total_kgco2'],
#                         'phases': list(phases_data)
#                     })
                
#                 cities_data.append({
#                     'city': city['city'],
#                     'total_carbon_co2': city_total['total_carbon_co2'],
#                     'total_kgco2': city_total['total_kgco2'],
#                     'buildings': buildings_data
#                 })
            
#             nested_structure.append({
#                 'region': region['region'],
#                 'total_carbon_co2': region_total['total_carbon_co2'],
#                 'total_kgco2': region_total['total_kgco2'],
#                 'cities': cities_data
#             })

#         serializer = self.get_serializer(queryset, many=True)
#         return Response({
#             'results': serializer.data,
#             'overall_aggregates': aggregate_data,
#             'material_type_aggregates': list(material_type_aggregates),
#             'carbon_status_totals': {
#                 'estimate': {
#                     'total_carbon_co2': carbon_status_sums['estimate_carbon'] or 0,
#                     'total_kgco2': carbon_status_sums['estimate_kgco2'] or 0
#                 },
#                 'actual': {
#                     'total_carbon_co2': carbon_status_sums['actual_carbon'] or 0,
#                     'total_kgco2': carbon_status_sums['actual_kgco2'] or 0
#                 }
#             },
#             'carbon_status_percentage': {
#                 'estimate': estimate_percentage,
#                 'actual': actual_percentage,
#             },
#             'region_aggregates': list(region_aggregates),
#             'city_aggregates': list(city_aggregates),
#             'building_aggregates': list(building_aggregates),
#             'phase_aggregates': list(phase_aggregates),
#             'nested_structure': nested_structure  # Newly added nested structure
#         })
        

from django.db.models import Sum
from rest_framework.response import Response
from rest_framework import status

class DesignDataAPIView(generics.GenericAPIView, mixins.ListModelMixin, mixins.CreateModelMixin,
                        mixins.UpdateModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin):
    
    queryset = DesignData.objects.all().order_by('id')
    serializer_class = DesignDataSerializer

    def get_object(self, id):
        try:
            return DesignData.objects.get(id=id)
        except DesignData.DoesNotExist:
            raise Http404

    def get(self, request, id=None, *args, **kwargs):
        if id:
            id_obj = self.get_object(id)
            serializer = DesignDataSerializer(id_obj)
            return Response(serializer.data)
        else:
            # Fetch all data
            alldata = DesignData.objects.all()
            serializer = DesignDataSerializer(alldata, many=True)
            
            # Calculate totals for each field
            totals = alldata.aggregate(
                substructure_total=Sum('substructure'),
                superstructure_total=Sum('superstructure'),
                facade_total=Sum('façade'),
                internal_walls_partitions_total=Sum('internal_walls_partitions'),
                internal_finishes_total=Sum('internal_finishes'),
                ff_fe_total=Sum('ff_fe')
            )
            
            # Calculate the grand total by summing these aggregated fields
            grand_total = sum(totals.values())
            
            # Prepare response with data, field totals, and grand total
            response_data = {
                "data": serializer.data,
                "totals": totals,
                "grand_total": grand_total
            }
            return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = DesignDataSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id=None, *args, **kwargs):
        agent_type = self.get_object(id)
        serializer = DesignDataSerializer(agent_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            DesignData.objects.filter(id=id).delete()
            message = {"success": "successfully deleted"}
            return Response(message, status=status.HTTP_200_OK)
        except Exception as e:
            error = getattr(e, 'message', repr(e))
            return Response(error, status=status.HTTP_400_BAD_REQUEST)





class YourMaterialAPIView(generics.GenericAPIView,mixins.ListModelMixin, mixins.CreateModelMixin,mixins.UpdateModelMixin,mixins.RetrieveModelMixin, mixins.DestroyModelMixin):

    queryset = YourMaterial.objects.all().order_by('id')
    serializer_class = YourMaterialSerializer

    def get_object(self, id):
        try:

            return YourMaterial.objects.get(id=id)
        except YourMaterial.DoesNotExist:
            raise Http404

    def get(self, request,id=None, *args, **kwargs):
        if id:
            id_obj = self.get_object(id)
            serializer = YourMaterialSerializer(id_obj)
            return Response(serializer.data)
        else:
            alldata = YourMaterial.objects.all()
            serializer = YourMaterialSerializer(alldata, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = YourMaterialSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request,id=None, *args, **kwargs):
        agent_type = self.get_object(id)
        serializer = YourMaterialSerializer(agent_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # data = serializer.data
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            YourMaterial.objects.filter(id=id).delete()
            message = {"success": "sucessfully deleted"}
            return Response(message, status=status.HTTP_200_OK)
        except Exception as e:
            error = getattr(e, 'message', repr(e))
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        



class YourMaterialEmissionAPIView(generics.GenericAPIView,mixins.ListModelMixin, mixins.CreateModelMixin,mixins.UpdateModelMixin,mixins.RetrieveModelMixin, mixins.DestroyModelMixin):

    queryset = YourMaterialEmission.objects.all().order_by('id')
    serializer_class = YourMaterialEmissionSerializer

    def get_object(self, id):
        try:

            return YourMaterialEmission.objects.get(id=id)
        except YourMaterialEmission.DoesNotExist:
            raise Http404

    def get(self, request,id=None, *args, **kwargs):
        if id:
            id_obj = self.get_object(id)
            serializer = YourMaterialEmissionSerializer(id_obj)
            return Response(serializer.data)
        else:
            alldata = YourMaterialEmission.objects.all()
            serializer = YourMaterialEmissionSerializer(alldata, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = YourMaterialEmissionSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request,id=None, *args, **kwargs):
        agent_type = self.get_object(id)
        serializer = YourMaterialEmissionSerializer(agent_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # data = serializer.data
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            YourMaterialEmission.objects.filter(id=id).delete()
            message = {"success": "sucessfully deleted"}
            return Response(message, status=status.HTTP_200_OK)
        except Exception as e:
            error = getattr(e, 'message', repr(e))
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        

class EcoMaterialAPIView(generics.GenericAPIView,mixins.ListModelMixin, mixins.CreateModelMixin,mixins.UpdateModelMixin,mixins.RetrieveModelMixin, mixins.DestroyModelMixin):

    queryset = EcoMaterial.objects.all().order_by('id')
    serializer_class = EcoMaterialSerializer

    def get_object(self, id):
        try:

            return EcoMaterial.objects.get(id=id)
        except EcoMaterial.DoesNotExist:
            raise Http404

    def get(self, request,id=None, *args, **kwargs):
        if id:
            id_obj = self.get_object(id)
            serializer = EcoMaterialSerializer(id_obj)
            return Response(serializer.data)
        else:
            alldata = EcoMaterial.objects.all()
            serializer = EcoMaterialSerializer(alldata, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = EcoMaterialSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request,id=None, *args, **kwargs):
        agent_type = self.get_object(id)
        serializer = EcoMaterialSerializer(agent_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # data = serializer.data
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            EcoMaterial.objects.filter(id=id).delete()
            message = {"success": "sucessfully deleted"}
            return Response(message, status=status.HTTP_200_OK)
        except Exception as e:
            error = getattr(e, 'message', repr(e))
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        

class EcoMaterialEmissionAPIView(generics.GenericAPIView,mixins.ListModelMixin, mixins.CreateModelMixin,mixins.UpdateModelMixin,mixins.RetrieveModelMixin, mixins.DestroyModelMixin):

    queryset = EcoMaterialEmission.objects.all().order_by('id')
    serializer_class = EcoMaterialEmissionSerializer

    def get_object(self, id):
        try:

            return EcoMaterialEmission.objects.get(id=id)
        except EcoMaterialEmission.DoesNotExist:
            raise Http404

    def get(self, request,id=None, *args, **kwargs):
        if id:
            id_obj = self.get_object(id)
            serializer = EcoMaterialEmissionSerializer(id_obj)
            return Response(serializer.data)
        else:
            alldata = EcoMaterialEmission.objects.all()
            serializer = EcoMaterialEmissionSerializer(alldata, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = EcoMaterialEmissionSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request,id=None, *args, **kwargs):
        agent_type = self.get_object(id)
        serializer = EcoMaterialEmissionSerializer(agent_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # data = serializer.data
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            EcoMaterialEmission.objects.filter(id=id).delete()
            message = {"success": "sucessfully deleted"}
            return Response(message, status=status.HTTP_200_OK)
        except Exception as e:
            error = getattr(e, 'message', repr(e))
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

class VolumeAPIView(generics.GenericAPIView,mixins.ListModelMixin, mixins.CreateModelMixin,mixins.UpdateModelMixin,mixins.RetrieveModelMixin, mixins.DestroyModelMixin):

    queryset = Volume.objects.all().order_by('id')
    serializer_class = VolumeSerializer

    def get_object(self, id):
        try:

            return Volume.objects.get(id=id)
        except Volume.DoesNotExist:
            raise Http404

    def get(self, request,id=None, *args, **kwargs):
        if id:
            id_obj = self.get_object(id)
            serializer = VolumeSerializer(id_obj)
            return Response(serializer.data)
        else:
            alldata = Volume.objects.all()
            serializer = VolumeSerializer(alldata, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = VolumeSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request,id=None, *args, **kwargs):
        agent_type = self.get_object(id)
        serializer = VolumeSerializer(agent_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # data = serializer.data
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            Volume.objects.filter(id=id).delete()
            message = {"success": "sucessfully deleted"}
            return Response(message, status=status.HTTP_200_OK)
        except Exception as e:
            error = getattr(e, 'message', repr(e))
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        


class CompareCarbonInputAPIView(generics.GenericAPIView,mixins.ListModelMixin, mixins.CreateModelMixin,mixins.UpdateModelMixin,mixins.RetrieveModelMixin, mixins.DestroyModelMixin):

    queryset = CompareCarbon.objects.all().order_by('id')
    serializer_class = CompareCarbonInputSerializer

    def get_object(self, id):
        try:

            return CompareCarbon.objects.get(id=id)
        except CompareCarbon.DoesNotExist:
            raise Http404

    def get(self, request,id=None, *args, **kwargs):
        if id:
            id_obj = self.get_object(id)
            serializer = CompareCarbonInputSerializer(id_obj)
            return Response(serializer.data)
        else:
            alldata = CompareCarbon.objects.all()
            serializer = CompareCarbonInputSerializer(alldata, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = CompareCarbonInputSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request,id=None, *args, **kwargs):
        agent_type = self.get_object(id)
        serializer = CompareCarbonInputSerializer(agent_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # data = serializer.data
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            CompareCarbon.objects.filter(id=id).delete()
            message = {"success": "sucessfully deleted"}
            return Response(message, status=status.HTTP_200_OK)
        except Exception as e:
            error = getattr(e, 'message', repr(e))
            return Response(error, status=status.HTTP_400_BAD_REQUEST)




class CompareCarbonAPIView(generics.GenericAPIView,mixins.ListModelMixin, mixins.CreateModelMixin,mixins.UpdateModelMixin,mixins.RetrieveModelMixin, mixins.DestroyModelMixin):

    queryset = CompareCarbon.objects.all().order_by('id')
    serializer_class = CompareCarbonSerializer
    # filter_backends = (CustomSearchFilter, OrderingFilter)
    # search_fields= '__all__'
    def get_object(self, id):
        try:

            return CompareCarbon.objects.get(id=id)
        except CompareCarbon.DoesNotExist:
            raise Http404

    def get(self, request,id=None, *args, **kwargs):
        if id:
            id_obj = self.get_object(id)
            serializer = CompareCarbonSerializer(id_obj)
            return Response(serializer.data)
        else:
            alldata = CompareCarbon.objects.all()
            serializer = CompareCarbonSerializer(alldata, many=True)
            return Response(serializer.data)