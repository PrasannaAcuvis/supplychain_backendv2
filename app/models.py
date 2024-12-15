from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    username = None  # Remove the default username field
    email = models.EmailField(unique=True)  # Set email as unique identifier
    cognito_sub = models.CharField(max_length=100, unique=True, null=True, blank=True)
    email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'  # Set email as the primary identifier
    REQUIRED_FIELDS = []  # No additional required fields

    def __str__(self):
        return self.email

class BestMatch(models.Model):
    delivery_note_ref_no = models.CharField(db_column='Delivery_Note_Ref_No',max_length=300, null=True, blank=True)
    supplier_name = models.TextField(db_column='Supplier_Name', null=True, blank=True)
    supplier_address_line_1 = models.TextField(db_column='Supplier_Address_Line_1', null=True, blank=True)
    supplier_city = models.TextField(db_column='Supplier_City', null=True, blank=True)
    supplier_post_code = models.TextField(db_column='Supplier_Post_code',null=True, blank=True)
    supplier_country = models.TextField(db_column='Supplier_Country', null=True, blank=True)
    delivery_to = models.TextField(db_column='Delivery_to', null=True, blank=True)
    delivery_address_line_1 = models.TextField(db_column='Delivery_Address_Line_1', null=True, blank=True)
    delivery_city = models.TextField(db_column='Delivery_City',null=True, blank=True)
    delivery_post_code = models.TextField(db_column='Delivery_Post_code',null=True, blank=True)
    delivery_country = models.TextField(db_column='Delivery_Country', null=True, blank=True)
    delivery_note_date = models.DateField(db_column='Delivery_Note_Date', null=True, blank=True)
    email = models.TextField(db_column='Email', null=True, blank=True)
    phone = models.TextField(db_column='Phone', null=True, blank=True)
    purchase_order_no = models.TextField(db_column='Purchase_Order_No',null=True, blank=True)
    filename = models.TextField(db_column='Filename', null=True, blank=True)
    account_number = models.TextField(db_column='account_number',null=True, blank=True)
    item_no = models.BigIntegerField(db_column='Item_No', null=True, blank=True)
    phase_id = models.BigIntegerField(db_column='Phase_ID', null=True, blank=True)
    product_description = models.TextField(db_column='Product_Description', null=True, blank=True)
    unit_of_measure = models.TextField(db_column='Unit_of_Measure', null=True, blank=True)
    quantity = models.FloatField(db_column='Quantity', null=True, blank=True)
    building_id = models.BigIntegerField(db_column='Building_ID',null=True, blank=True)
    entry_time = models.DateTimeField(db_column='entry_time', null=True, blank=True)
    user_id = models.TextField(db_column='User_ID', null=True, blank=True)
    product_name = models.TextField(db_column='Product_Name', null=True, blank=True)
    material_name = models.TextField(db_column='Material_Name',null=True, blank=True)
    product_company_name = models.TextField(db_column='Product_Company_Name', null=True, blank=True)
    product_match_score = models.FloatField(db_column='Product_Match_Score', null=True, blank=True)
    global_warming_potential_fossil = models.FloatField(db_column='global_warming_potential_fossil', null=True, blank=True)
    declared_unit = models.TextField(db_column='Declared_Unit', null=True, blank=True)
    scaling_factor = models.FloatField(db_column='Scaling_factor', null=True, blank=True)
    data_source = models.TextField(db_column='Data_Source', null=True, blank=True)
    processed = models.BooleanField(db_column='Processed', default=False, null=True, blank=True)
    processed_timestamp = models.DateTimeField(db_column='Processed_Timestamp', null=True, blank=True)
    kgco2 = models.FloatField(db_column='KgCO2', null=True, blank=True)

    class Meta:
        db_table = 'app_deliverynote_data'

class Phase(models.Model):
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name

class InvoiceData(models.Model):
    customer_ref = models.BigIntegerField(default=12346, null=True, blank=True)
    delivery_note_ref_no = models.BigIntegerField(null=True, blank=True)
    supplier_name = models.CharField(max_length=300, null=True, blank=True)
    data_source = models.CharField(max_length=300, null=True, blank=True)
    product_description = models.CharField(max_length=1000, null=True, blank=True)
    material_name = models.CharField(max_length=500)
    entry_time = models.DateField(null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    unit_of_measure = models.CharField(max_length=300, null=True, blank=True)
    country_name = models.CharField(max_length=300, default='UK', null=True, blank=True,db_index=True)
    region_name = models.CharField(max_length=300, default='London', null=True, blank=True,db_index=True)
    city_name = models.CharField(max_length=300, default='Westminster', null=True, blank=True,db_index=True)
    building_name = models.CharField(max_length=300, default='John Wood Hospital', null=True, blank=True,db_index=True)
    phase_name = models.ForeignKey(Phase, null=True, blank=True, on_delete=models.CASCADE)
    kgco2 = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Invoice {self.customer_ref}"

    class Meta:
        db_table = 'invoice_data'


class Country(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Region(models.Model):
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='regions')

    def __str__(self):
        return f"{self.name}, {self.country.name}"
    
class City(models.Model):
    name = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='cities')

    def __str__(self):
        return f"{self.name}, {self.region.name}"

class Building(models.Model):
    name = models.CharField(max_length=100)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='buildings')

    def __str__(self):
        return f"{self.name}, {self.city.name}"




class DesignData(models.Model):
    region = models.CharField(max_length=300)
    city = models.CharField(max_length=300)
    building_name = models.CharField(max_length=300)
    substructure =models.IntegerField()
    superstructure=models.IntegerField()
    façade =models.IntegerField()
    internal_walls_partitions =models.IntegerField()
    internal_finishes =models.IntegerField()
    ff_fe =models.IntegerField()
    gia = models.IntegerField()


    def __str__(self):
        return self.name


class YourMaterial(models.Model):
    name = models.CharField(max_length=300)
    class Meta:
        db_table = 'your_material_table'

    def __str__(self):
        return self.name
class YourMaterialEmission(models.Model):
    name=models.ForeignKey(YourMaterial,null=True,on_delete=models.CASCADE)
    emission=models.IntegerField(null=True)
    class Meta:
        db_table = 'your_material_emission_table'

    def __str__(self):
        return str(self.name)

class EcoMaterial(models.Model):
    name=models.CharField(max_length=300)
    class Meta:
        db_table = 'eco_material_table'

    def __str__(self):
        return self.name

class EcoMaterialEmission(models.Model):
    name=models.ForeignKey(EcoMaterial,null=True,on_delete=models.CASCADE)
    emission=models.IntegerField(null=True)
    class Meta:
        db_table = 'eco_material_emission_table'

    def __str__(self):
        return str(self.name)

class Volume(models.Model):
    value=models.IntegerField(null=True)
    class Meta:
        db_table = 'volume_table'

    def __str__(self):
        return str(self.value)


class CompareCarbon(models.Model):
    country=models.ForeignKey(Country,null=True,on_delete=models.CASCADE)
    region=models.ForeignKey(Region,null=True,on_delete=models.CASCADE)
    #your_material=models.ForeignKey(YourMaterial,null=True,related_name="carbon_table",on_delete=models.CASCADE)
    your_material_emission=models.ForeignKey(YourMaterialEmission,null=True,related_name="carbon_table",on_delete=models.CASCADE)
    #eco_material=models.ForeignKey(EcoMaterial,null=True,related_name="carbon_table",on_delete=models.CASCADE)
    eco_material_emission=models.ForeignKey(EcoMaterialEmission,null=True,related_name="carbon_table",on_delete=models.CASCADE)
    volume=models.ForeignKey(Volume,null=True,on_delete=models.CASCADE)

    @property
    def total_reduction_potential(self):
        return (self.volume.value)*((self.your_material_emission.emission)-(self.eco_material_emission.emission))
    
    @property
    def reduction_potential(self):
        return (self.total_reduction_potential)/((self.your_material_emission.emission)*(self.volume.value))*100
    
    @property
    def trees_planted(self):
        return (self.total_reduction_potential)/(58.8)
    
    @property
    def energy_used(self):
        return (self.total_reduction_potential)/(10000)
    
    @property
    def car_journeys(self):
        return (self.total_reduction_potential)/(0.25)

    class Meta:
        db_table = 'carbon_table'












