# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "2f8fd291-5f12-4dc2-9767-a65a5f4eaf3c",
# META       "default_lakehouse_name": "RDS_retail_LH_Sitecore_Bronze",
# META       "default_lakehouse_workspace_id": "1e4482f3-5d7d-4467-a879-66ae1e48a0f1",
# META       "known_lakehouses": [
# META         {
# META           "id": "2f8fd291-5f12-4dc2-9767-a65a5f4eaf3c"
# META         },
# META         {
# META           "id": "5f0850a1-37a9-44ac-9039-79f45f44acde"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Pre-create Bronze Lakehouse Entity Delta Tables 
# 
# Use this notebook to create the tables for the Bronze lake entities.

# MARKDOWN ********************

# ### Module Imports

# CELL ********************

from pyspark.sql.types import *
from delta.tables import DeltaTable
from datetime import datetime, timezone

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create Change Data State table in Bronze Lake

# CELL ********************

print("Creating Change Data Feed Table")
table_names = [
    "AddressAssignments",
    "Addresses",
    "Catalogs",
    "Categories",
    "Orders",
    "Products",
    "UserGroupAssignments",
    "UserGroups",
    "Users"
]
current_timestamp = datetime.now(timezone.utc)

spark.createDataFrame([(0, current_timestamp, item) for item in table_names], \
    ["last_processed_commit_version", "last_processed_timestamp", "table_name"])\
    .write.mode("overwrite").format("delta").save('Tables/ChangeDataFeedState')

display(spark.read.format("delta").table("ChangeDataFeedState"))


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create AddressAssignments table in Bronze Lake

# CELL ********************

print("Creating AddressAssignments Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/AddressAssignments") \
    .addColumn("Route", dataType=StringType(), nullable=True)\
    .addColumn("RouteParams", StructType([
        StructField("buyerID", StringType(), True),
        StructField("addressID", StringType(), True)
    ]), nullable=True)\
    .addColumn("QueryParams", StructType([
        StructField("userID", StringType(), True),
        StructField("userGroupID", StringType(), True)
    ]), nullable=True)\
    .addColumn("Verb", dataType=StringType(), nullable=True)\
    .addColumn("Date", dataType=StringType(), nullable=True)\
    .addColumn("LogID", dataType=StringType(), nullable=True)\
    .addColumn("UserToken", dataType=StringType(), nullable=True)\
    .addColumn("Request", StructType([
        StructField("Body", StructType([
            StructField("UserID", StringType(), True),
            StructField("UserGroupID", StringType(), True),
            StructField("AddressID", StringType(), True),
        ]), nullable=True),
        StructField("Headers", StringType(), True)
    ]), nullable=True)\
    .addColumn("Response", StructType([
        StructField("Body", StructType([
            StructField("Errors", ArrayType(StructType([
                StructField("ErrorCode", StringType(), True),
                StructField("Message", StringType(), True),
                StructField("Data", StructType([
                    StructField("ObjectType", StringType(), True),
                    StructField("ObjectID", StringType(), True)
                ]), nullable=True),
            ])), nullable=True),
        ]), nullable=True),
        StructField("Headers", StringType(), True)
    ]), nullable=True)\
    .addColumn("ConfigData", dataType=StringType(), nullable=True)\
    .addColumn("EventProcessedUtcTime", dataType=TimestampType(), nullable=True)\
    .addColumn("PartitionId", dataType=LongType(), nullable=True)\
    .addColumn("EventEnqueuedUtcTime", dataType=TimestampType(), nullable=True)\
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create Addresses Table in the Bronze Lake

# CELL ********************

print("Creating Addresses Table")
DeltaTable.createOrReplace(spark)\
    .location("Tables/Addresses")\
    .addColumn("Route", StringType(), nullable=True)\
    .addColumn("RouteParams", StructType([
        StructField("buyerID", StringType(), True),
        StructField("addressID", StringType(), True)
    ]), nullable=True)\
    .addColumn("Verb", StringType(), nullable=True)\
    .addColumn("Date", StringType(), nullable=True)\
    .addColumn("LogID", StringType(), nullable=True)\
    .addColumn("UserToken", StringType(), nullable=True)\
    .addColumn("Request", StructType([
        StructField("Body", StructType([
            StructField("ID", StringType(), True),
            StructField("CompanyName", StringType(), True),
            StructField("FirstName", StringType(), True),
            StructField("LastName", StringType(), True),
            StructField("Street1", StringType(), True),
            StructField("Street2", StringType(), True),
            StructField("City", StringType(), True),
            StructField("State", StringType(), True),
            StructField("Zip", StringType(), True),
            StructField("Country", StringType(), True),
            StructField("Phone", StringType(), True),
            StructField("AddressName", StringType(), True),
            StructField("xp", StringType(), True),
        ]), nullable=True),
        StructField("Headers", StringType(), True)\
    ]), nullable=True)\
    .addColumn("Response", StructType([
        StructField("Body", StructType([
            StructField("ID", StringType(), True),
            StructField("CompanyName", StringType(), True),
            StructField("FirstName", StringType(), True),
            StructField("LastName", StringType(), True),
            StructField("Street1", StringType(), True),
            StructField("Street2", StringType(), True),
            StructField("City", StringType(), True),
            StructField("State", StringType(), True),
            StructField("Zip", StringType(), True),
            StructField("Country", StringType(), True),
            StructField("Phone", StringType(), True),
            StructField("AddressName", StringType(), True),
            StructField("xp", StringType(), True),
            StructField("DateCreated", StringType(), True),
        ]), nullable=True),
        StructField("Headers", StringType(), True)\
    ]), nullable=True)\
    .addColumn("ConfigData", StringType(), nullable=True)\
    .addColumn("EventProcessedUtcTime", TimestampType(), nullable=True)\
    .addColumn("PartitionId", LongType(), nullable=True)\
    .addColumn("EventEnqueuedUtcTime", TimestampType(), nullable=True)\
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create Catalogs Table in the Bronze Lake

# CELL ********************

print("Creating Catalogs Table")
DeltaTable.createOrReplace(spark)\
    .location("Tables/Catalogs")\
    .addColumn("Route", StringType(), True)\
    .addColumn("RouteParams", StructType([
        StructField("catalogID", StringType(), True)
    ]), True)\
    .addColumn("Verb", StringType(), True)\
    .addColumn("Date", StringType(), True)\
    .addColumn("LogID", StringType(), True)\
    .addColumn("UserToken", StringType(), True)\
    .addColumn("Request", StructType([
        StructField("Body", StructType([
            StructField("ID", StringType(), True),
            StructField("OwnerID", StringType(), True),
            StructField("Name", StringType(), True),
            StructField("Description", StringType(), True),
            StructField("Active", BooleanType(), True),
            StructField("xp", StringType(), True),
        ]), True),
        StructField("Headers", StringType(), True)
    ]), True)\
    .addColumn("Response", StructType([
        StructField("Body", StructType([
            StructField("ID", StringType(), True),
            StructField("OwnerID", StringType(), True),
            StructField("Name", StringType(), True),
            StructField("Description", StringType(), True),
            StructField("Active", BooleanType(), True),
            StructField("CategoryCount", LongType(), True),
            StructField("xp", StringType(), True),
        ]), True),
        StructField("Headers", StringType(), True)
    ]), True)\
    .addColumn("ConfigData", StringType(), True)\
    .addColumn("EventProcessedUtcTime", TimestampType(), True)\
    .addColumn("PartitionId", LongType(), True)\
    .addColumn("EventEnqueuedUtcTime", TimestampType(), True)\
    .property("delta.enableChangeDataFeed", "true")\
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create Categories Table in the Bronze Lake

# CELL ********************

print("Creating Categories Table")
DeltaTable.createOrReplace(spark)\
    .location("Tables/Categories")\
    .addColumn("Route", StringType(), True)\
    .addColumn("RouteParams", StructType([
        StructField("catalogID", StringType(), True),
        StructField("categoryID", StringType(), True)
    ]), True)\
    .addColumn("Verb", StringType(), True)\
    .addColumn("Date", StringType(), True)\
    .addColumn("LogID", StringType(), True)\
    .addColumn("UserToken", StringType(), True)\
    .addColumn("Request", StructType([
        StructField("Body", StructType([
            StructField("ID", StringType(), True),
            StructField("Name", StringType(), True),
            StructField("Description", StringType(), True),
            StructField("ListOrder", LongType(), True),
            StructField("Active", BooleanType(), True),
            StructField("ParentID", StringType(), True),
            StructField("ChildCount", LongType(), True),
            StructField("xp", StringType(), True)
        ]), True),
        StructField("Headers", StringType(), True)
    ]), True)\
    .addColumn("Response", StructType([
        StructField("Body", StructType([
            StructField("ID", StringType(), True),
            StructField("Name", StringType(), True),
            StructField("Description", StringType(), True),
            StructField("ListOrder", LongType(), True),
            StructField("Active", BooleanType(), True),
            StructField("ParentID", StringType(), True),
            StructField("ChildCount", LongType(), True),
            StructField("xp", StringType(), True)
        ]), True),
        StructField("Headers", StringType(), True)
    ]), True)\
    .addColumn("ConfigData", StringType(), True)\
    .addColumn("EventProcessedUtcTime", TimestampType(), True)\
    .addColumn("PartitionId", LongType(), True)\
    .addColumn("EventEnqueuedUtcTime", TimestampType(), True)\
    .property("delta.enableChangeDataFeed", "true")\
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create Orders Table in the Bronze Lake

# CELL ********************

DeltaTable.createOrReplace(spark)\
    .location("Tables/Orders")\
    .addColumn("ID", dataType=StringType(), nullable=True)\
    .addColumn("FromUser", StructType([
        StructField("ID", StringType(), True),
        StructField("CompanyID", StringType(), True),
        StructField("Username", StringType(), True),
        StructField("Password", StringType(), True),
        StructField("FirstName", StringType(), True),
        StructField("LastName", StringType(), True),
        StructField("Email", StringType(), True),
        StructField("Phone", StringType(), True),
        StructField("TermsAccepted", StringType(), True),
        StructField("Active", BooleanType(), True),
        StructField("xp", StringType(), True),
        StructField("AvailableRoles", StringType(), True),
        StructField("Locale", StringType(), True),
        StructField("DateCreated", StringType(), True),
        StructField("PasswordLastSetDate", StringType(), True)
    ]), nullable=True)\
    .addColumn("FromCompanyID", dataType=StringType(), nullable=True)\
    .addColumn("ToCompanyID", dataType=StringType(), nullable=True)\
    .addColumn("FromUserID", dataType=StringType(), nullable=True)\
    .addColumn("BillingAddressID", dataType=StringType(), nullable=True)\
    .addColumn("BillingAddress", dataType=StringType(), nullable=True)\
    .addColumn("ShippingAddressID", dataType=StringType(), nullable=True)\
    .addColumn("Comments", dataType=StringType(), nullable=True)\
    .addColumn("LineItemCount", dataType=LongType(), nullable=True)\
    .addColumn("Status", dataType=LongType(), nullable=True)\
    .addColumn("DateCreated", dataType=StringType(), nullable=True)\
    .addColumn("DateSubmitted", dataType=StringType(), nullable=True)\
    .addColumn("DateApproved", dataType=StringType(), nullable=True)\
    .addColumn("DateDeclined", dataType=StringType(), nullable=True)\
    .addColumn("DateCanceled", dataType=StringType(), nullable=True)\
    .addColumn("DateCompleted", dataType=StringType(), nullable=True)\
    .addColumn("LastUpdated", dataType=StringType(), nullable=True)\
    .addColumn("Subtotal", dataType=DoubleType(), nullable=True)\
    .addColumn("ShippingCost", dataType=DoubleType(), nullable=True)\
    .addColumn("TaxCost", dataType=DoubleType(), nullable=True)\
    .addColumn("PromotionDiscount", dataType=DoubleType(), nullable=True)\
    .addColumn("Currency", dataType=StringType(), nullable=True)\
    .addColumn("Total", dataType=DoubleType(), nullable=True)\
    .addColumn("IsSubmitted", dataType=BooleanType(), nullable=True)\
    .addColumn("SubscriptionID", dataType=StringType(), nullable=True)\
    .addColumn("xp", dataType=StringType(), nullable=True)\
    .addColumn("LineItems", ArrayType(StructType([
        StructField("ID", StringType(), True),
        StructField("ProductID", StringType(), True),
        StructField("Quantity", LongType(), True),
        StructField("BundleItemID", StringType(), True),
        StructField("IsBundle", BooleanType(), True),
        StructField("DateAdded", StringType(), True),
        StructField("QuantityShipped", LongType(), True),
        StructField("UnitPrice", DoubleType(), True),
        StructField("PromotionDiscount", DoubleType(), True),
        StructField("LineTotal", DoubleType(), True),
        StructField("LineSubtotal", DoubleType(), True),
        StructField("CostCenter", StringType(), True),
        StructField("DateNeeded", StringType(), True),
        StructField("ShippingAccount", StringType(), True),
        StructField("ShippingAddressID", StringType(), True),
        StructField("ShipFromAddressID", StringType(), True),
        StructField("Product", StructType([
            StructField("ID", StringType(), True),
            StructField("Name", StringType(), True),
            StructField("Description", StringType(), True),
            StructField("Returnable", BooleanType(), True),
            StructField("QuantityMultiplier", LongType(), True),
            StructField("ShipWeight", StringType(), True),
            StructField("ShipHeight", StringType(), True),
            StructField("ShipWidth", StringType(), True),
            StructField("ShipLength", StringType(), True),
            StructField("DefaultSupplierID", StringType(), True),
            StructField("ParentID", StringType(), True),
            StructField("xp", StringType(), True)
        ]), True),
        StructField("Variant", StringType(), True),
        StructField("ShippingAddress", StringType(), True),
        StructField("ShipFromAddress", StringType(), True),
        StructField("SupplierID", StringType(), True),
        StructField("InventoryRecordID", StringType(), True),
        StructField("PriceScheduleID", StringType(), True),
        StructField("PriceOverridden", BooleanType(), True),
        StructField("Specs", ArrayType(StringType()), True),
        StructField("xp", StringType(), True),
    ])), nullable=True)\
    .addColumn("Shipments", ArrayType(StringType()), True)\
    .addColumn("Payments", ArrayType(StringType()), True)\
    .addColumn("UserContext", StructType([
        StructField("ID", StringType(), True),
        StructField("AnonymousID", StringType(), True),
    ]), nullable=True)\
    .addColumn("EventProcessedUtcTime", dataType=TimestampType(), nullable=True)\
    .addColumn("PartitionId", dataType=LongType(), nullable=True)\
    .addColumn("EventEnqueuedUtcTime", dataType=TimestampType(), nullable=True)\
    .property("delta.enableChangeDataFeed", "true")\
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create Products table in Bronze Lake

# CELL ********************

print("Creating Products Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/Products") \
    .addColumn("UserContext", StructType([
        StructField("ID", StringType(), True),
        StructField("AnonymousID", StringType(), True)
    ]), nullable=True)\
    .addColumn("ProductID", dataType=StringType(), nullable=True)\
    .addColumn("Marketplace", dataType=StringType(), nullable=True)\
    .addColumn("OwnerID", dataType=StringType(), nullable=True)\
    .addColumn("Name", dataType=StringType(), nullable=True)\
    .addColumn("Description", dataType=StringType(), nullable=True)\
    .addColumn("QuantityMultiplier", dataType=LongType(), nullable=True)\
    .addColumn("ShipWeight", dataType=DoubleType(), nullable=True)\
    .addColumn("ShipHeight", dataType=DoubleType(), nullable=True)\
    .addColumn("ShipWidth", dataType=DoubleType(), nullable=True)\
    .addColumn("ShipLength", dataType=DoubleType(), nullable=True)\
    .addColumn("Active", dataType=BooleanType(), nullable=True)\
    .addColumn("AutoForward", dataType=BooleanType(), nullable=True)\
    .addColumn("SpecCount", dataType=LongType(), nullable=True)\
    .addColumn("VariantCount", dataType=LongType(), nullable=True)\
    .addColumn("ShipFromAddressID", dataType=StringType(), nullable=True)\
    .addColumn("Inventory", dataType=StructType([
        StructField("Enabled", BooleanType(), True),
        StructField("NotificationPoint", LongType(), True),
        StructField("VariantLevelTracking", BooleanType(), True),
        StructField("OrderCanExceed", BooleanType(), True),
        StructField("QuantityAvailable", LongType(), True),
        StructField("LastUpdated", StringType(), True)
    ]), nullable=True)\
    .addColumn("DefaultSupplierID", dataType=StringType(), nullable=True)\
    .addColumn("AllSuppliersCanSell", dataType=BooleanType(), nullable=True)\
    .addColumn("DefaultPriceScheduleID", dataType=StringType(), nullable=True)\
    .addColumn("Returnable", dataType=BooleanType(), nullable=True)\
    .addColumn("xp", dataType=StringType(), nullable=True)\
    .addColumn("Catalogs", ArrayType(StringType()), nullable=True)\
    .addColumn("Categories", ArrayType(StructType([
        StructField("ID", StringType(), True),
        StructField("ListOrder", LongType(), True)
    ])), nullable=True)\
    .addColumn("Suppliers", ArrayType(StringType()), nullable=True)\
    .addColumn("Buyers",ArrayType(StringType()), nullable=True)\
    .addColumn("UserGroups", ArrayType(StringType()), nullable=True)\
    .addColumn("Specs", ArrayType(StructType([
        StructField("OwnerID", StringType(), True),
        StructField("ID", StringType(), True),
        StructField("ListOrder", LongType(), True),
        StructField("Name", StringType(), True),
        StructField("DefaultValue", StringType(), True),
        StructField("Required", BooleanType(), True),
        StructField("AllowOpenText", BooleanType(), True),
        StructField("DefaultOptionID", StringType(), True),
        StructField("DefinesVariant", BooleanType(), True),
        StructField("xp", StringType(), True),
        StructField("OptionCount", LongType(), True),
        StructField("Options", ArrayType(StructType([
            StructField("ID", StringType(), True),
            StructField("Value", StringType(), True),
            StructField("ListOrder", LongType(), True),
            StructField("IsOpenText", BooleanType(), True),
            StructField("PriceMarkupType", StringType(), True),
            StructField("PriceMarkup", DoubleType(), True),
            StructField("xp", StringType(), True),
        ])), True)
    ])), nullable=True)\
    .addColumn("EventProcessedUtcTime", dataType=TimestampType(), nullable=True)\
    .addColumn("PartitionId", dataType=LongType(), nullable=True)\
    .addColumn("EventEnqueuedUtcTime", dataType=TimestampType(), nullable=True)\
    .property("delta.enableChangeDataFeed", "true") \
    .execute()


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create Users table in Bronze Lake

# CELL ********************

print("Creating Users Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/Users") \
    .addColumn("Route", StringType(), nullable=True) \
    .addColumn("RouteParams", StructType([
        StructField("buyerID", StringType(), True),
        StructField("userID", StringType(), True)
    ]), nullable=True) \
    .addColumn("Verb", StringType(), nullable=True) \
    .addColumn("Date", StringType(), nullable=True) \
    .addColumn("LogID", StringType(), nullable=True) \
    .addColumn("UserToken", StringType(), nullable=True) \
    .addColumn("Request", StructType([
        StructField("Body", StructType([
            StructField("Username", StringType(), True),
            StructField("FirstName", StringType(), True),
            StructField("LastName", StringType(), True),
            StructField("Email", StringType(), True),
            StructField("Phone", StringType(), True),
            StructField("TermsAccepted", StringType(), True),
            StructField("Active", BooleanType(), True),
            StructField("Password", StringType(), True),
            StructField("xp", StringType(), True),
            StructField("CompanyID", StringType(), True),
            StructField("ID", StringType(), True),
        ]), nullable=True),
        StructField("Headers", StringType(), True)
    ]), nullable=True) \
    .addColumn("Response", StructType([
        StructField("Body", StructType([
            StructField("ID", StringType(), True),
            StructField("CompanyID", StringType(), True),
            StructField("Username", StringType(), True),
            StructField("Password", StringType(), True),
            StructField("FirstName", StringType(), True),
            StructField("LastName", StringType(), True),
            StructField("Email", StringType(), True),
            StructField("Phone", StringType(), True),
            StructField("TermsAccepted", StringType(), True),
            StructField("Active", BooleanType(), True),
            StructField("xp", StringType(), True),
            StructField("AvailableRoles", StringType(), True),
            StructField("Locale", StringType(), True),
            StructField("DateCreated", StringType(), True),
            StructField("PasswordLastSetDate", StringType(), True),
        ]), nullable=True),
        StructField("Headers", StringType(), True)
    ]), nullable=True) \
    .addColumn("ConfigData", StringType(), nullable=True) \
    .addColumn("EventProcessedUtcTime", TimestampType(), nullable=True) \
    .addColumn("PartitionId", LongType(), nullable=True) \
    .addColumn("EventEnqueuedUtcTime", TimestampType(), nullable=True) \
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create UserGroupAssignments table in Bronze Lake

# CELL ********************

print("Creating UserGroupAssignments Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/UserGroupAssignments") \
    .addColumn("Route", dataType=StringType(), nullable=True)\
    .addColumn("RouteParams", StructType([
        StructField("buyerID", StringType(), True),
        StructField("userGroupID", StringType(), True),
        StructField("userID", StringType(), True)
    ]), nullable=True)\
    .addColumn("Verb", dataType=StringType(), nullable=True)\
    .addColumn("Date", dataType=StringType(), nullable=True)\
    .addColumn("LogID", dataType=StringType(), nullable=True)\
    .addColumn("UserToken", dataType=StringType(), nullable=True)\
    .addColumn("Request", StructType([
        StructField("Body", StructType([
            StructField("UserGroupID", StringType(), True),
            StructField("UserID", StringType(), True)
        ]), nullable=True)
    ]), nullable=True)\
    .addColumn("Response", StructType([
        StructField("Body", StructType([
            StructField("Errors", ArrayType(
                StructType([
                    StructField("Data", StructType([
                        StructField("ObjectID", StringType(), True),
                        StructField("ObjectType", StringType(), True)
                    ]), nullable=True),
                    StructField("ErrorCode", StringType(), True),
                    StructField("Message", StringType(), True)
                ]),
                True
            ), True)
        ]), nullable=True)
    ]), nullable=True)\
    .addColumn("ConfigData", dataType=StringType(), nullable=True)\
    .addColumn("EventEnqueuedUtcTime", dataType=TimestampType(), nullable=True)\
    .addColumn("PartitionId", dataType=LongType(), nullable=True)\
    .addColumn("EventProcessedUtcTime", dataType=TimestampType(), nullable=True)\
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Create UserGroups table in Bronze Lake

# CELL ********************

print("Creating UserGroups Table")
DeltaTable.createOrReplace(spark) \
    .location("Tables/UserGroups") \
    .addColumn("Route", dataType=StringType(), nullable=True)\
    .addColumn("RouteParams", StructType([
        StructField("buyerID", StringType(), True),
        StructField("userGroupID", StringType(), True)
    ]), nullable=True)\
    .addColumn("Verb", dataType=StringType(), nullable=True)\
    .addColumn("Date", dataType=StringType(), nullable=True)\
    .addColumn("LogID", dataType=StringType(), nullable=True)\
    .addColumn("UserToken", dataType=StringType(), nullable=True)\
    .addColumn("Request", StructType([
        StructField("Body", StructType([
            StructField("ID", StringType(), True),
            StructField("Name", StringType(), True),
            StructField("Description", StringType(), True),
            StructField("xp", StringType(), True),
        ]), nullable=True),
        StructField("Headers", StringType(), True)
    ]), nullable=True)\
    .addColumn("Response", StructType([
        StructField("Body", StructType([
            StructField("ID", StringType(), True),
            StructField("Name", StringType(), True),
            StructField("Description", StringType(), True),
            StructField("xp", StringType(), True),
        ]), nullable=True),
        StructField("Headers", StringType(), True)
    ]), nullable=True)\
    .addColumn("ConfigData", dataType=StringType(), nullable=True)\
    .addColumn("EventProcessedUtcTime", dataType=TimestampType(), nullable=True)\
    .addColumn("PartitionId", dataType=LongType(), nullable=True)\
    .addColumn("EventEnqueuedUtcTime", dataType=TimestampType(), nullable=True)\
    .property("delta.enableChangeDataFeed", "true") \
    .execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### Add sample data into Bronze Datalake
# Overwrite the tables with sample data generated using the C# data generator

# CELL ********************

from pyspark.sql.functions import to_timestamp
import pyspark.sql.functions as F

spark.conf.set('spark.sql.parquet.vorder.enabled', 'false')   

bronze_lakehouse_directory_name = "QA_Data_Files"
upload_deletions = False
mode = "overwrite"

dfAddrAssignments = spark.read.json("Files/{0}/addressAssignments.json".format(bronze_lakehouse_directory_name))
dfAddrAssignments = dfAddrAssignments.withColumn("EventEnqueuedUtcTime", to_timestamp("EventEnqueuedUtcTime"))
dfAddrAssignments = dfAddrAssignments.withColumn("EventProcessedUtcTime", to_timestamp("EventProcessedUtcTime"))
dfAddrAssignments.write.format("delta").mode(mode).save("Tables/AddressAssignments")

dfAddresses = spark.read.json("Files/{0}/addresses.json".format(bronze_lakehouse_directory_name))
dfAddresses = dfAddresses.withColumn("EventEnqueuedUtcTime", to_timestamp("EventEnqueuedUtcTime"))
dfAddresses = dfAddresses.withColumn("EventProcessedUtcTime", to_timestamp("EventProcessedUtcTime"))
dfAddresses.write.format("delta").mode(mode).save("Tables/Addresses")

dfCatalogs = spark.read.json("Files/{0}/catalogs.json".format(bronze_lakehouse_directory_name))
dfCatalogs = dfCatalogs.withColumn("EventEnqueuedUtcTime", to_timestamp("EventEnqueuedUtcTime"))
dfCatalogs = dfCatalogs.withColumn("EventProcessedUtcTime", to_timestamp("EventProcessedUtcTime"))
dfCatalogs.write.format("delta").mode(mode).save("Tables/Catalogs")

dfCategories = spark.read.json("Files/{0}/categories.json".format(bronze_lakehouse_directory_name))
dfCategories = dfCategories.withColumn("EventEnqueuedUtcTime", to_timestamp("EventEnqueuedUtcTime"))
dfCategories = dfCategories.withColumn("EventProcessedUtcTime", to_timestamp("EventProcessedUtcTime"))
dfCategories.write.format("delta").mode(mode).save("Tables/Categories")

dfOrders = spark.read.json("Files/{0}/orders.json".format(bronze_lakehouse_directory_name))
dfOrders = dfOrders.withColumn("EventEnqueuedUtcTime", to_timestamp("EventEnqueuedUtcTime"))
dfOrders = dfOrders.withColumn("EventProcessedUtcTime", to_timestamp("EventProcessedUtcTime"))
dfOrders.write.format("delta").mode(mode).save("Tables/Orders")

dfProducts = spark.read.json("Files/{0}/products.json".format(bronze_lakehouse_directory_name))
dfProducts = dfProducts.withColumn("EventEnqueuedUtcTime", to_timestamp("EventEnqueuedUtcTime"))
dfProducts = dfProducts.withColumn("EventProcessedUtcTime", to_timestamp("EventProcessedUtcTime"))
dfProducts = dfProducts.withColumn("Specs", F.when(F.col("Specs") == F.array(), F.lit(None) ))
dfProducts.write.format("delta").mode(mode).save("Tables/Products")

dfUGAssignments = spark.read.json("Files/{0}/userGroupAssignments.json".format(bronze_lakehouse_directory_name))
dfUGAssignments = dfUGAssignments.withColumn("EventEnqueuedUtcTime", to_timestamp("EventEnqueuedUtcTime"))
dfUGAssignments = dfUGAssignments.withColumn("EventProcessedUtcTime", to_timestamp("EventProcessedUtcTime"))
dfUGAssignments.write.format("delta").mode(mode).save("Tables/UserGroupAssignments")

dfUserGroups = spark.read.json("Files/{0}/userGroups.json".format(bronze_lakehouse_directory_name))
dfUserGroups = dfUserGroups.withColumn("EventEnqueuedUtcTime", to_timestamp("EventEnqueuedUtcTime"))
dfUserGroups = dfUserGroups.withColumn("EventProcessedUtcTime", to_timestamp("EventProcessedUtcTime"))
dfUserGroups.write.format("delta").mode(mode).save("Tables/UserGroups")

dfUsers = spark.read.json("Files/{0}/users.json".format(bronze_lakehouse_directory_name))
dfUsers = dfUsers.withColumn("EventEnqueuedUtcTime", to_timestamp("EventEnqueuedUtcTime"))
dfUsers = dfUsers.withColumn("EventProcessedUtcTime", to_timestamp("EventProcessedUtcTime"))
dfUsers.write.format("delta").mode(mode).save("Tables/Users")

# Deletions
if upload_deletions:
    print("Uploading deletion data")
    deleteDfAddrAssignments = spark.read.json("Files/{0}/addressAssignments_deletions.json".format(bronze_lakehouse_directory_name))
    deleteDfAddrAssignments = deleteDfAddrAssignments.withColumn("EventEnqueuedUtcTime", to_timestamp("EventEnqueuedUtcTime"))
    deleteDfAddrAssignments = deleteDfAddrAssignments.withColumn("EventProcessedUtcTime", to_timestamp("EventProcessedUtcTime"))
    deleteDfAddrAssignments.write.format("delta").mode("append").save("Tables/AddressAssignments")

    deleteDfUGAssignments = spark.read.json("Files/{0}/userGroupAssignments_deletions.json".format(bronze_lakehouse_directory_name))
    deleteDfUGAssignments = deleteDfUGAssignments.withColumn("EventEnqueuedUtcTime", to_timestamp("EventEnqueuedUtcTime"))
    deleteDfUGAssignments = deleteDfUGAssignments.withColumn("EventProcessedUtcTime", to_timestamp("EventProcessedUtcTime"))
    deleteDfUGAssignments.write.format("delta").mode("append").save("Tables/UserGroupAssignments")

    deleteDfUsers = spark.read.json("Files/{0}/users_deletions.json".format(bronze_lakehouse_directory_name))
    deleteDfUsers = deleteDfUsers.withColumn("Date", to_timestamp("Date"))
    deleteDfUsers = deleteDfUsers.withColumn("EventEnqueuedUtcTime", to_timestamp("EventEnqueuedUtcTime"))
    deleteDfUsers = deleteDfUsers.withColumn("EventProcessedUtcTime", to_timestamp("EventProcessedUtcTime"))
    deleteDfUsers.write.format("delta").mode("append").save("Tables/Users")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
