# Generated by Django 3.2.20 on 2024-12-15 11:28

import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='BestMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delivery_note_ref_no', models.CharField(db_column='Delivery_Note_Ref_No', max_length=100)),
                ('item_no', models.CharField(db_column='Item_No', max_length=50)),
                ('product_description', models.CharField(db_column='Product_Description', max_length=255)),
                ('unit_of_measure', models.CharField(db_column='Unit_of_Measure', max_length=50)),
                ('quantity', models.FloatField(db_column='Quantity')),
                ('product_name', models.CharField(blank=True, db_column='Product_Name', max_length=255, null=True)),
                ('material_name', models.CharField(blank=True, db_column='Material_Name', max_length=255, null=True)),
                ('product_company_name', models.CharField(blank=True, db_column='Product_Company_Name', max_length=255, null=True)),
                ('product_match_score', models.FloatField(blank=True, db_column='Product_Match_Score', null=True)),
                ('global_warming_potential_fossil', models.FloatField(blank=True, db_column='global_warming_potential_fossil', null=True)),
                ('declared_unit', models.CharField(blank=True, db_column='Declared_Unit', max_length=50, null=True)),
                ('scaling_factor', models.FloatField(blank=True, db_column='Scaling_factor', null=True)),
                ('data_source', models.CharField(blank=True, db_column='Data_Source', max_length=255, null=True)),
                ('processed', models.BooleanField(db_column='Processed', default=False)),
                ('processed_timestamp', models.DateTimeField(blank=True, db_column='Processed_Timestamp', null=True)),
                ('gia', models.FloatField(db_column='gia', default=5000)),
                ('building_id', models.CharField(blank=True, db_column='Building_ID', max_length=50, null=True)),
                ('kgco2', models.FloatField(blank=True, db_column='KgCO2', null=True)),
                ('supplier_name', models.CharField(blank=True, db_column='Supplier_Name', max_length=255, null=True)),
                ('supplier_address_line_1', models.CharField(blank=True, db_column='Supplier_Address_Line_1', max_length=255, null=True)),
                ('supplier_city', models.CharField(blank=True, db_column='Supplier_City', max_length=255, null=True)),
                ('supplier_post_code', models.CharField(blank=True, db_column='Supplier_Post_code', max_length=20, null=True)),
                ('supplier_country', models.CharField(blank=True, db_column='Supplier_Country', max_length=100, null=True)),
                ('delivery_to', models.CharField(blank=True, db_column='Delivery_to', max_length=255, null=True)),
                ('delivery_address_line_1', models.CharField(blank=True, db_column='Delivery_Address_Line_1', max_length=255, null=True)),
                ('delivery_city', models.CharField(blank=True, db_column='Delivery_City', max_length=255, null=True)),
                ('delivery_post_code', models.CharField(blank=True, db_column='Delivery_Post_code', max_length=20, null=True)),
                ('delivery_country', models.CharField(blank=True, db_column='Delivery_Country', max_length=100, null=True)),
                ('delivery_note_date', models.DateField(blank=True, db_column='Delivery_Note_Date', null=True)),
                ('email', models.EmailField(blank=True, db_column='Email', max_length=254, null=True)),
                ('phone', models.CharField(blank=True, db_column='Phone', max_length=20, null=True)),
                ('purchase_order_no', models.CharField(blank=True, db_column='Purchase_Order_No', max_length=100, null=True)),
                ('filename', models.CharField(blank=True, db_column='Filename', max_length=255, null=True)),
                ('account_number', models.CharField(blank=True, db_column='account_number', max_length=100, null=True)),
                ('entry_time', models.DateTimeField(blank=True, db_column='entry_time', null=True)),
                ('phase_id', models.CharField(blank=True, db_column='Phase_ID', max_length=50, null=True)),
                ('user_id', models.CharField(blank=True, db_column='User_ID', max_length=50, null=True)),
            ],
            options={
                'db_table': 'app_deliverynote_data',
            },
        ),
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='DesignData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('region', models.CharField(max_length=300)),
                ('city', models.CharField(max_length=300)),
                ('building_name', models.CharField(max_length=300)),
                ('substructure', models.IntegerField()),
                ('superstructure', models.IntegerField()),
                ('façade', models.IntegerField()),
                ('internal_walls_partitions', models.IntegerField()),
                ('internal_finishes', models.IntegerField()),
                ('ff_fe', models.IntegerField()),
                ('gia', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='EcoMaterial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=300)),
            ],
            options={
                'db_table': 'eco_material_table',
            },
        ),
        migrations.CreateModel(
            name='Phase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=300)),
            ],
        ),
        migrations.CreateModel(
            name='Volume',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.IntegerField(null=True)),
            ],
            options={
                'db_table': 'volume_table',
            },
        ),
        migrations.CreateModel(
            name='YourMaterial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=300)),
            ],
            options={
                'db_table': 'your_material_table',
            },
        ),
        migrations.CreateModel(
            name='YourMaterialEmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emission', models.IntegerField(null=True)),
                ('name', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='app.yourmaterial')),
            ],
            options={
                'db_table': 'your_material_emission_table',
            },
        ),
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='regions', to='app.country')),
            ],
        ),
        migrations.CreateModel(
            name='InvoiceData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('customer_ref', models.BigIntegerField(blank=True, default=12346, null=True)),
                ('delivery_note_ref_no', models.BigIntegerField(blank=True, null=True)),
                ('supplier_name', models.CharField(blank=True, max_length=300, null=True)),
                ('data_source', models.CharField(blank=True, max_length=300, null=True)),
                ('product_description', models.CharField(blank=True, max_length=1000, null=True)),
                ('material_name', models.CharField(max_length=500)),
                ('entry_time', models.DateField(blank=True, null=True)),
                ('quantity', models.IntegerField(blank=True, null=True)),
                ('unit_of_measure', models.CharField(blank=True, max_length=300, null=True)),
                ('country_name', models.CharField(blank=True, db_index=True, default='UK', max_length=300, null=True)),
                ('region_name', models.CharField(blank=True, db_index=True, default='London', max_length=300, null=True)),
                ('city_name', models.CharField(blank=True, db_index=True, default='Westminster', max_length=300, null=True)),
                ('building_name', models.CharField(blank=True, db_index=True, default='John Wood Hospital', max_length=300, null=True)),
                ('kgco2', models.BigIntegerField(blank=True, null=True)),
                ('phase_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='app.phase')),
            ],
            options={
                'db_table': 'invoice_data',
            },
        ),
        migrations.CreateModel(
            name='EcoMaterialEmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emission', models.IntegerField(null=True)),
                ('name', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='app.ecomaterial')),
            ],
            options={
                'db_table': 'eco_material_emission_table',
            },
        ),
        migrations.CreateModel(
            name='CompareCarbon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('country', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='app.country')),
                ('eco_material_emission', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='carbon_table', to='app.ecomaterialemission')),
                ('region', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='app.region')),
                ('volume', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='app.volume')),
                ('your_material_emission', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='carbon_table', to='app.yourmaterialemission')),
            ],
            options={
                'db_table': 'carbon_table',
            },
        ),
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('region', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cities', to='app.region')),
            ],
        ),
        migrations.CreateModel(
            name='Building',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('city', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='buildings', to='app.city')),
            ],
        ),
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('cognito_sub', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('email_verified', models.BooleanField(default=False)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
