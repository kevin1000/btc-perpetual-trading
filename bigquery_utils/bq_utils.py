"""
library containing bigquery functions
"""
import logging
from google.cloud import bigquery

logger = logging.getLogger()


def write_data(table_id, data: [dict]) -> bool:
    """
    Function writing data to a bigquery table
    :param table_id: Bigquery table ID
    :param data: Data formatted as array of dicts to be inserted in Bigquery
    :return: A boolean of the status of the import
    """
    client = bigquery.Client()

    errors = client.insert_rows_json(table_id, data, row_ids=[None] * len(data))
    if errors:
        logger.error("Encountered errors while inserting rows: %s", errors)
        insert_status = False
    else:
        insert_status = True
    return insert_status


def read_data(query: str) -> [dict]:
    bqclient = bigquery.Client()
    df = (
    bqclient.query(query)
        .result()
        .to_dataframe(
            # Optionally, explicitly request to use the BigQuery Storage API. As of
            # google-cloud-bigquery version 1.26.0 and above, the BigQuery Storage
            # API is used by default.
            create_bqstorage_client=True,
        )
    )
    return df


def load_array_dict(table_id: str, schema: [], df):
    client = bigquery.Client()

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_TRUNCATE",
    )

    job = client.load_table_from_dataframe(
        df, table_id, job_config=job_config
    )
    job.result()

    table = client.get_table(table_id)
    print(
        "Loaded {} rows and {} columns to {}".format(
            table.num_rows, len(table.schema), table_id
        )
    )
