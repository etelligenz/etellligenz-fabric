# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "4cefd373-9fab-4a17-ab1a-db5d44985fbc",
# META       "default_lakehouse_name": "Purview",
# META       "default_lakehouse_workspace_id": "1e4482f3-5d7d-4467-a879-66ae1e48a0f1",
# META       "known_lakehouses": [
# META         {
# META           "id": "4cefd373-9fab-4a17-ab1a-db5d44985fbc"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

from notebookutils import mssparkutils
mssparkutils.fs.help()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

mssparkutils.fs.help("ls")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

full_tables = mssparkutils.fs.ls("Files/DEH/DomainModel")
full_tables

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql.types import *
def loadFullDataFromSource(table_name):
    df = spark.read.format("parquet").load('Files/DEH/DomainModel/' + table_name)
    df.write.mode("overwrite").format("delta").saveAsTable(table_name)

for table in full_tables:
    loadFullDataFromSource(table.name)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df = spark.sql("SELECT * FROM Purview.businessdomain LIMIT 1000")
display(df)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
