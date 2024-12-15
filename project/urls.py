"""project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from app.views import *
from django.urls import path,include
urlpatterns = [
    # Country URLs
    path('api/country/', CountryListCreateAPI.as_view(), name='country-list-create'),
    path('api/country/<int:pk>/', CountryRetrieveUpdateDestroyAPI.as_view(), name='country-retrieve-update-destroy'),

    # Region URLs
    path('api/region/', RegionListCreateAPI.as_view(), name='region-list-create'),
    path('api/region/<int:pk>/', RegionRetrieveUpdateDestroyAPI.as_view(), name='region-retrieve-update-destroy'),

    # Building URLs
    path('api/building/', BuildingListCreateAPI.as_view(), name='building-list-create'),
    path('api/building/<int:pk>/', BuildingRetrieveUpdateDestroyAPI.as_view(), name='building-retrieve-update-destroy'),

    # User Signup and Verify Email
    path('api/login/', LoginAPI.as_view(), name='login'),  # New Login endpoint
    path('api/signup/', UserSignUpAPI.as_view(), name='user-signup'),
    path('api/user_list/', ListUsersAPI.as_view(), name='user-list'),  # New endpoint for listing all users
    path('api/user_list/<int:id>/', UserDetailAPI.as_view(), name='user-detail'),  # CRUD operations
    path('api/verify_email/', VerifyEmailAPI.as_view(), name='verify-email'),
    path('api/resend_otp/', ResendConfirmationCodeAPI.as_view(), name='resend-confirmation'),

    # Supplier URLs
    path('api/search/', InvoiceDataView.as_view()),

    path('api/design/', DesignDataAPIView.as_view()),
    path('api/design/<int:id>/',DesignDataAPIView.as_view()),

    path('best_match/', BestMatchAPIView.as_view(), name='best-match-list-create'),
    path('best_match/<int:pk>/', BestMatchAPIView.as_view(), name='best-match-retrieve-update-delete'),

    path('api/your_material/', YourMaterialAPIView.as_view()),
    path('api/your_material/<int:id>/',YourMaterialAPIView.as_view()),

    path('api/your_material_emission/', YourMaterialEmissionAPIView.as_view()),
    path('api/your_material_emission/<int:id>/',YourMaterialEmissionAPIView.as_view()),

    path('api/eco_material/', EcoMaterialAPIView.as_view()),
    path('api/eco_material/<int:id>/',EcoMaterialAPIView.as_view()),

    path('api/eco_material_emission/', EcoMaterialEmissionAPIView.as_view()),
    path('api/eco_material_emission/<int:id>/',EcoMaterialEmissionAPIView.as_view()),

    path('api/volume/', VolumeAPIView.as_view()),
    path('api/volume/<int:id>/',VolumeAPIView.as_view()),

    path('api/compare_carbon_input/', CompareCarbonInputAPIView.as_view()),
    path('api/compare_carbon_input/<int:id>/',CompareCarbonInputAPIView.as_view()),

    path('api/compare_carbon/', CompareCarbonAPIView.as_view()),
    path('api/compare_carbon/<int:id>/',CompareCarbonAPIView.as_view()),

    # CSV Uploads
    path('invoice_csv/', CSVUploadView.as_view(), name='upload_csv'),
    path('design_csv/', CSVUploadViewDesign.as_view(), name='upload_design'),
    path('country_csv/', CSVUploadViewCountry.as_view(), name='upload_country'),
    path('region_csv/', CSVUploadViewRegion.as_view(), name='upload_region'),
    path('city_csv/', CSVUploadViewCity.as_view(), name='upload_city'),
    path('building_csv/', CSVUploadViewBuilding.as_view(), name='upload_building'),
    path('your_material_csv/', CSVUploadViewYourMaterial.as_view(), name='upload_your_material'),
    path('your_material_emission_csv/', CSVUploadViewYourMaterialEmission.as_view(), name='upload_your_material_emission'),
    path('eco_material_csv/', CSVUploadViewEcoMaterial.as_view(), name='upload_eco_material'),
    path('eco_material_emission_csv/', CSVUploadViewEcoMaterialEmission.as_view(), name='upload_eco_material_emission'),
    
]