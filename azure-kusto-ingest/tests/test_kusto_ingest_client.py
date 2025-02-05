# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License
import io
import json
import os
import uuid
from pathlib import Path

import pytest
import responses
from mock import patch

from azure.kusto.data.data_format import DataFormat

from azure.kusto.ingest import QueuedIngestClient, IngestionProperties, IngestionStatus
from azure.kusto.ingest.exceptions import KustoInvalidEndpointError
from azure.kusto.ingest.managed_streaming_ingest_client import ManagedStreamingIngestClient

pandas_installed = False
try:
    import pandas

    pandas_installed = True
except:
    pass

UUID_REGEX = "[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
BLOB_NAME_REGEX = "database__table__" + UUID_REGEX + "__dataset.csv.gz"
BLOB_URL_REGEX = "https://storageaccount.blob.core.windows.net/tempstorage/database__table__" + UUID_REGEX + "__dataset.csv.gz[?]sas"
STORAGE_QUEUE_URL = "https://storageaccount.queue.core.windows.net/readyforaggregation-secured?sp=rl&st=2020-05-20T13:38:37Z&se=2020-05-21T13:38:37Z&sv=2019-10-10&sr=c&sig=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TEMP_STORAGE_URL = "https://storageaccount.blob.core.windows.net/tempstorage?sp=rl&st=2020-05-20T13:38:37Z&se=2020-05-21T13:38:37Z&sv=2019-10-10&sr=c&sig=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"


def request_callback(request):
    body = json.loads(request.body.decode()) if type(request.body) == bytes else json.loads(request.body)
    response_status = 400
    response_headers = dict()
    response_body = {}

    if ".get ingestion resources" in body["csl"]:
        response_status = 200
        response_body = {
            "Tables": [
                {
                    "TableName": "Table_0",
                    "Columns": [{"ColumnName": "ResourceTypeName", "DataType": "String"}, {"ColumnName": "StorageRoot", "DataType": "String"}],
                    "Rows": [
                        [
                            "SecuredReadyForAggregationQueue",
                            STORAGE_QUEUE_URL,
                        ],
                        [
                            "SecuredReadyForAggregationQueue",
                            STORAGE_QUEUE_URL,
                        ],
                        [
                            "SecuredReadyForAggregationQueue",
                            STORAGE_QUEUE_URL,
                        ],
                        [
                            "SecuredReadyForAggregationQueue",
                            STORAGE_QUEUE_URL,
                        ],
                        [
                            "SecuredReadyForAggregationQueue",
                            STORAGE_QUEUE_URL,
                        ],
                        [
                            "FailedIngestionsQueue",
                            "https://storageaccount.queue.core.windows.net/failedingestions?sp=rl&st=2020-05-20T13:38:37Z&se=2020-05-21T13:38:37Z&sv=2019-10-10&sr=c&sig=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                        ],
                        [
                            "SuccessfulIngestionsQueue",
                            "https://storageaccount.queue.core.windows.net/successfulingestions?sp=rl&st=2020-05-20T13:38:37Z&se=2020-05-21T13:38:37Z&sv=2019-10-10&sr=c&sig=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                        ],
                        [
                            "TempStorage",
                            TEMP_STORAGE_URL,
                        ],
                        [
                            "TempStorage",
                            TEMP_STORAGE_URL,
                        ],
                        [
                            "TempStorage",
                            TEMP_STORAGE_URL,
                        ],
                        [
                            "TempStorage",
                            TEMP_STORAGE_URL,
                        ],
                        [
                            "TempStorage",
                            TEMP_STORAGE_URL,
                        ],
                        [
                            "IngestionsStatusTable",
                            "https://storageaccount.table.core.windows.net/ingestionsstatus?sp=rl&st=2020-05-20T13:38:37Z&se=2020-05-21T13:38:37Z&sv=2019-10-10&sr=c&sig=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                        ],
                    ],
                }
            ]
        }

    if ".get kusto identity token" in body["csl"]:
        response_status = 200
        response_body = {
            "Tables": [{"TableName": "Table_0", "Columns": [{"ColumnName": "AuthorizationContext", "DataType": "String"}], "Rows": [["authorization_context"]]}]
        }

    return response_status, response_headers, json.dumps(response_body)


def request_error_callback(request):
    body = json.loads(request.body.decode()) if type(request.body) == bytes else json.loads(request.body)
    response_status = 400
    response_headers = dict()
    response_body = {}

    if ".get ingestion resources" in body["csl"]:
        response_status = 400
        response_body = {
            "error": {
                "code": "BadRequest",
                "message": "Request is invalid and cannot be executed.",
                "@type": "Kusto.Common.Svc.Exceptions.AdminCommandWrongEndpointException",
                "@message": "Cannot get ingestion resources from this service endpoint. The appropriate endpoint is most likely "
                "'https://ingest-somecluster.kusto.windows.net/'.",
                "@context": {
                    "timestamp": "2021-10-12T06:05:35.6602087Z",
                    "serviceAlias": "SomeCluster",
                    "machineName": "KEngine000000",
                    "processName": "Kusto.WinSvc.Svc",
                    "processId": 2648,
                    "threadId": 472,
                    "appDomainName": "Kusto.WinSvc.Svc.exe",
                    "clientRequestId": "KPC.execute;a3dfb878-9d2b-49d6-89a5-e9b3a9f1f674",
                    "activityId": "87eb8fc9-78b3-4580-bcc8-6c90482f9118",
                    "subActivityId": "bbfb038b-4467-4f96-afd4-945904fc6278",
                    "activityType": "DN.AdminCommand.IngestionResourcesGetCommand",
                    "parentActivityId": "00e678e9-4204-4143-8c94-6afd94c27430",
                    "activityStack": "(Activity stack: CRID=KPC.execute;a3dfb878-9d2b-49d6-89a5-e9b3a9f1f674 ARID=87eb8fc9-78b3-4580-bcc8-6c90482f9118 > DN.Admin.Client.ExecuteControlCommand/833dfb85-5d67-44b7-882d-eb2283e65780 > P.WCF.Service.ExecuteControlCommand..IInterNodeCommunicationAdminContract/3784e74f-1d89-4c15-adef-0a360c4c431e > DN.FE.ExecuteControlCommand/00e678e9-4204-4143-8c94-6afd94c27430 > DN.AdminCommand.IngestionResourcesGetCommand/bbfb038b-4467-4f96-afd4-945904fc6278)",
                },
                "@permanent": True,
            }
        }

    if ".show version" in body["csl"]:
        response_status = 200
        response_body = {
            "Tables": [
                {
                    "TableName": "Table_0",
                    "Columns": [
                        {"ColumnName": "BuildVersion", "DataType": "String"},
                        {"ColumnName": "BuildTime", "DataType": "DateTime"},
                        {"ColumnName": "ServiceType", "DataType": "String"},
                        {"ColumnName": "ProductVersion", "DataType": "String"},
                    ],
                    "Rows": [["1.0.0.0", "2000-01-01T00:00:00Z", "Engine", "2020-09-07 12-09-22"]],
                }
            ]
        }

    return response_status, response_headers, json.dumps(response_body)


def assert_queued_upload(mock_put_message_in_queue, mock_upload_blob_from_stream, expected_url: str, check_raw_data: bool = True, format: str = "csv"):
    # mock_put_message_in_queue
    assert mock_put_message_in_queue.call_count == 1

    put_message_in_queue_mock_kwargs = mock_put_message_in_queue.call_args_list[0][1]

    queued_message_json = json.loads(put_message_in_queue_mock_kwargs["content"])

    # mock_upload_blob_from_stream
    # not checking the query string because it can change order, just checking it's there
    assert queued_message_json["BlobPath"].startswith(expected_url) is True
    assert len(queued_message_json["BlobPath"]) > len(expected_url)
    assert queued_message_json["DatabaseName"] == "database"
    assert queued_message_json["IgnoreSizeLimit"] is False
    assert queued_message_json["AdditionalProperties"]["format"] == format
    assert queued_message_json["FlushImmediately"] is False
    assert queued_message_json["TableName"] == "table"
    if check_raw_data:
        assert queued_message_json["RawDataSize"] > 0
    assert queued_message_json["RetainBlobOnSuccess"] is True
    if mock_upload_blob_from_stream is not None:
        upload_blob_kwargs = mock_upload_blob_from_stream.call_args_list[0][1]
        assert issubclass(type(upload_blob_kwargs["data"]), io.BufferedIOBase)


@pytest.fixture(params=[QueuedIngestClient, ManagedStreamingIngestClient])
def ingest_client_class(request):
    if request.param == ManagedStreamingIngestClient:
        return ManagedStreamingIngestClient.from_dm_kcsb
    return request.param


class TestQueuedIngestClient:
    MOCKED_UUID_4 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    MOCKED_PID = 64
    MOCKED_TIME = 100

    @responses.activate
    @patch(
        "azure.kusto.ingest.managed_streaming_ingest_client.ManagedStreamingIngestClient.MAX_STREAMING_SIZE_IN_BYTES", new=0
    )  # Trick to always fallback to queued ingest
    @patch("azure.kusto.data.security._AadHelper.acquire_authorization_header", return_value=None)
    @patch("azure.storage.blob.BlobClient.upload_blob")
    @patch("azure.storage.queue.QueueClient.send_message")
    @patch("uuid.uuid4", return_value=MOCKED_UUID_4)
    def test_sanity_ingest_from_file(self, mock_uuid, mock_put_message_in_queue, mock_upload_blob_from_stream, mock_aad, ingest_client_class):
        responses.add_callback(
            responses.POST, "https://ingest-somecluster.kusto.windows.net/v1/rest/mgmt", callback=request_callback, content_type="application/json"
        )

        ingest_client = ingest_client_class("https://ingest-somecluster.kusto.windows.net")
        ingestion_properties = IngestionProperties(database="database", table="table", data_format=DataFormat.CSV)

        # ensure test can work when executed from within directories
        current_dir = os.getcwd()
        path_parts = ["azure-kusto-ingest", "tests", "input", "dataset.csv"]
        missing_path_parts = []
        for path_part in path_parts:
            if path_part not in current_dir:
                missing_path_parts.append(path_part)

        file_path = os.path.join(current_dir, *missing_path_parts)

        result = ingest_client.ingest_from_file(file_path, ingestion_properties=ingestion_properties)

        assert result.status == IngestionStatus.QUEUED

        assert_queued_upload(
            mock_put_message_in_queue,
            mock_upload_blob_from_stream,
            "https://storageaccount.blob.core.windows.net/tempstorage/database__table__11111111-1111-1111-1111-111111111111__dataset.csv.gz?",
        )

    @responses.activate
    @patch("azure.kusto.ingest.managed_streaming_ingest_client.ManagedStreamingIngestClient.MAX_STREAMING_SIZE_IN_BYTES", new=0)
    def test_ingest_from_file_wrong_endpoint(self, ingest_client_class):
        responses.add_callback(
            responses.POST, "https://somecluster.kusto.windows.net/v1/rest/mgmt", callback=request_error_callback, content_type="application/json"
        )

        ingest_client = ingest_client_class("https://somecluster.kusto.windows.net")
        ingestion_properties = IngestionProperties(database="database", table="table", data_format=DataFormat.CSV)

        current_dir = os.getcwd()
        path_parts = ["azure-kusto-ingest", "tests", "input", "dataset.csv"]
        missing_path_parts = []
        for path_part in path_parts:
            if path_part not in current_dir:
                missing_path_parts.append(path_part)

        file_path = os.path.join(current_dir, *missing_path_parts)

        with pytest.raises(KustoInvalidEndpointError) as ex:
            ingest_client.ingest_from_file(file_path, ingestion_properties=ingestion_properties)

        assert (
            ex.value.args[0] == "You are using 'DataManagement' client type, but the provided endpoint is of ServiceType 'Engine'. Initialize the "
            "client with the appropriate endpoint URI: 'https://ingest-somecluster.kusto.windows.net'"
        ), ("Expected exception was " "not raised")

    @responses.activate
    @pytest.mark.skipif(not pandas_installed, reason="requires pandas")
    @patch("azure.kusto.ingest.managed_streaming_ingest_client.ManagedStreamingIngestClient.MAX_STREAMING_SIZE_IN_BYTES", new=0)
    @patch("azure.storage.blob.BlobClient.upload_blob")
    @patch("azure.storage.queue.QueueClient.send_message")
    @patch("uuid.uuid4", return_value=MOCKED_UUID_4)
    @patch("time.time", return_value=MOCKED_TIME)
    @patch("os.getpid", return_value=MOCKED_PID)
    def test_simple_ingest_from_dataframe(self, mock_pid, mock_time, mock_uuid, mock_put_message_in_queue, mock_upload_blob_from_stream, ingest_client_class):
        responses.add_callback(
            responses.POST, "https://ingest-somecluster.kusto.windows.net/v1/rest/mgmt", callback=request_callback, content_type="application/json"
        )

        ingest_client = ingest_client_class("https://ingest-somecluster.kusto.windows.net")
        ingestion_properties = IngestionProperties(database="database", table="table", data_format=DataFormat.CSV)

        from pandas import DataFrame

        fields = ["id", "name", "value"]
        rows = [[1, "abc", 15.3], [2, "cde", 99.9]]
        df = DataFrame(data=rows, columns=fields)

        result = ingest_client.ingest_from_dataframe(df, ingestion_properties=ingestion_properties)
        assert result.status == IngestionStatus.QUEUED

        expected_url = "https://storageaccount.blob.core.windows.net/tempstorage/database__table__11111111-1111-1111-1111-111111111111__df_{0}_100_11111111-1111-1111-1111-111111111111.csv.gz?".format(
            id(df)
        )

        assert_queued_upload(mock_put_message_in_queue, mock_upload_blob_from_stream, expected_url)

    @responses.activate
    @patch("azure.kusto.ingest.managed_streaming_ingest_client.ManagedStreamingIngestClient.MAX_STREAMING_SIZE_IN_BYTES", new=0)
    @patch("azure.kusto.data.security._AadHelper.acquire_authorization_header", return_value=None)
    @patch("azure.storage.blob.BlobClient.upload_blob")
    @patch("azure.storage.queue.QueueClient.send_message")
    @patch("uuid.uuid4", return_value=MOCKED_UUID_4)
    def test_sanity_ingest_from_stream(self, mock_uuid, mock_put_message_in_queue, mock_upload_blob_from_stream, mock_aad, ingest_client_class):
        responses.add_callback(
            responses.POST, "https://ingest-somecluster.kusto.windows.net/v1/rest/mgmt", callback=request_callback, content_type="application/json"
        )

        ingest_client = ingest_client_class("https://ingest-somecluster.kusto.windows.net")
        ingestion_properties = IngestionProperties(database="database", table="table", data_format=DataFormat.CSV)

        # ensure test can work when executed from within directories
        current_dir = os.getcwd()
        path_parts = ["azure-kusto-ingest", "tests", "input", "dataset.csv"]
        missing_path_parts = []

        for path_part in path_parts:
            if path_part not in current_dir:
                missing_path_parts.append(path_part)

        file_path = os.path.join(current_dir, *missing_path_parts)

        result = ingest_client.ingest_from_stream(io.StringIO(Path(file_path).read_text()), ingestion_properties=ingestion_properties)
        assert result.status == IngestionStatus.QUEUED

        assert_queued_upload(
            mock_put_message_in_queue,
            mock_upload_blob_from_stream,
            "https://storageaccount.blob.core.windows.net/tempstorage/database__table__11111111-1111-1111-1111-111111111111__stream.gz?",
            check_raw_data=False,
        )
