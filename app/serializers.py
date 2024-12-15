from rest_framework import serializers
from .models import *
from datetime import datetime
import pytz

class BestMatchSerializer(serializers.ModelSerializer):
    # Computed fields
    carbon = serializers.SerializerMethodField()
    kgco2_per_m2 = serializers.SerializerMethodField()

    class Meta:
        model = BestMatch
        fields = [
            "id",
            "delivery_note_ref_no",
            "item_no",
            "product_description",
            "unit_of_measure",
            "quantity",
            "product_name",
            "material_name",
            "product_company_name",
            "product_match_score",
            "global_warming_potential_fossil",
            "declared_unit",
            "scaling_factor",
            "data_source",
            "processed",
            "processed_timestamp",
           # "gia",
            "carbon",
            "kgco2_per_m2"
        ]
        read_only_fields = [
            "product_name",
            "material_name",
            "product_company_name",
            "product_match_score",
            "global_warming_potential_fossil",
            "declared_unit",
            "scaling_factor",
            "data_source",
            "processed",
            "processed_timestamp",
            "carbon",
            "kgco2_per_m2"
        ]

    def get_carbon(self, obj):
        try:
            if obj.global_warming_potential_fossil and obj.scaling_factor:
                return float(obj.global_warming_potential_fossil) / float(obj.scaling_factor)
        except (ValueError, TypeError):
            return None
        return None

    def get_kgco2_per_m2(self, obj):
        try:
            if obj.global_warming_potential_fossil and obj.scaling_factor and obj.quantity:
                return (float(obj.global_warming_potential_fossil) / float(obj.scaling_factor)) * (float(obj.quantity) / float(5000))
        except (ValueError, TypeError):
            return None
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        processed_timestamp = instance.processed_timestamp

        if processed_timestamp:
            # Format the date-time to the desired format
            formatted_date = processed_timestamp.strftime("%Y-%m-%d %H:%M:%S.%f%z")
            # Replace +0000 with +00 to represent UTC
            formatted_date = formatted_date[:-5] + "+00"
            data['processed_timestamp'] = formatted_date

        return data

class InvoiceDataSerializer(serializers.ModelSerializer):
    phase_name = serializers.CharField(source='phase_name.name', read_only=True)
    class Meta:
        model = InvoiceData
        fields = '__all__'



class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'

class RegionSerializer(serializers.ModelSerializer):
    country = serializers.CharField(source='country.name')
    class Meta:
        model = Region
        fields = ['id','name','country']  # Adjust fields if you need to filter some out

class CitySerializer(serializers.ModelSerializer):
    region = serializers.CharField(source='region.name')
    class Meta:
        model = City
        fields = ['id','name','region'] 


class BuildingSerializer(serializers.ModelSerializer):
    city=serializers.CharField(source='city.name')
    class Meta:
        model = Building
        fields = ['id', 'name', 'city']


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    confirm_password = serializers.CharField(write_only=True, required=False)



    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'password', 'confirm_password','email_verified']

    def validate(self, data):
        if 'password' in data and 'confirm_password' in data:
            if data['password'] != data['confirm_password']:
                raise serializers.ValidationError("Passwords do not match")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        user = CustomUser.objects.create(
            email=validated_data['email'],
        )
        if 'password' in validated_data:
            user.set_password(validated_data['password'])
        user.save()
        return user

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            instance.set_password(validated_data.pop('password'))
        return super().update(instance, validated_data)


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class ResendCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)



class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)


class UserListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    email_verified = serializers.BooleanField(default=False)

class DesignDataSerializer(serializers.ModelSerializer):
    total = serializers.SerializerMethodField()

    class Meta:
        model = DesignData
        fields = ['id', 'region', 'city', 'building_name', 'substructure', 'superstructure', 
                  'façade', 'internal_walls_partitions', 'internal_finishes', 'ff_fe', 'gia', 'total']

    def get_total(self, obj):
        # Calculate the total by summing the specified fields
        return (
            obj.substructure +
            obj.superstructure +
            obj.façade +
            obj.internal_walls_partitions +
            obj.internal_finishes +
            obj.ff_fe
        )

class YourMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = YourMaterial
        fields = '__all__'  # Adjust fields if you need to filter some out


class YourMaterialEmissionSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='name.name')
    class Meta:
        model = YourMaterialEmission
        fields = '__all__'  # Adjust fields if you need to filter some out


class EcoMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = EcoMaterial
        fields = '__all__'  # Adjust fields if you need to filter some out


class EcoMaterialEmissionSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='name.name')
    class Meta:
        model = EcoMaterialEmission
        fields = '__all__'  # Adjust fields if you need to filter some out


class VolumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volume
        fields = '__all__'  # Adjust fields if you need to filter some out

class CompareCarbonInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompareCarbon
        fields = ('id','country','region','your_material_emission','eco_material_emission','volume')
    # def validate(self, data):
    #     your_material = data.get('your_material')
    #     your_material_emission = data.get('your_material_emission')
        
    #     if your_material and your_material_emission:
    #         if your_material_emission.name != your_material:
    #             raise serializers.ValidationError("The emission does not match the selected material.")
            #     return data






class CompareCarbonSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source='region.country')
    region_name=serializers.CharField(source='region.name')
    material_name=serializers.CharField(source='your_material_emission.name')
    material_emission_value=serializers.CharField(source='your_material_emission.emission')
    eco_material_name=serializers.CharField(source='eco_material_emission.name')
    eco_emission_value=serializers.CharField(source='eco_material_emission.emission')
    volume_value=serializers.IntegerField(source='volume.value')
    total_reduction_potential = serializers.IntegerField()
    reduction_potential = serializers.IntegerField()
    trees_planted = serializers.IntegerField()
    energy_used = serializers.IntegerField()
    car_journeys = serializers.IntegerField()
    class Meta:
        model = CompareCarbon
        fields = ('country_name','region_name','material_name','material_emission_value','eco_material_name','eco_emission_value','volume_value','total_reduction_potential','reduction_potential','trees_planted','energy_used','car_journeys')