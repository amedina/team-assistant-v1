**The overall system**

We are working on a multi agent system called the Team Assistant. The Team assitant consists of various specialized agents all contributing to the effective execution of the team mission.

This system is in development. Your task is to help me continue the development process. It is important to keep continuity and always improve on the implementation we have.

**Data Ingestion**

The system includes a data ingestion and retrieval data sub-system:

1. Vertex AI Vector Search Index
2. Google Cloud PostgrSQL Database
3. Neo4j Knowledge Graph Database

**Connectors**
Data is ingested and retrieved into/from these storage targets through data connectors:

data_ingestion/connectors/base_connector.py
data_ingestion/connectors/drive_connector.py
data_ingestion/connectors/github_connector.py
data_ingestion/connectors/web_connector.py

**Architecture**
The data ingestion system implements a Coordinator Pattern:

**_Managers (Orchestration Layer)_**:
data_ingestion/managers/vector_store_manager.py
data_ingestion/managers/database_manager.py
data_ingestion/managers/knowledge_graph_manager.py

**_Ingestors (Storage Layer)_**
data_ingestion/ingestors/vector_store_ingestor.py
data_ingestion/ingestors/database_ingestor.py
data_ingestion/ingestors/knowledge_graph_ingestor.py

**_Retrievers (Query Layer)_**
data_ingestion/retrievers/vector_store_retrievers.py
data_ingestion/retrievers/database_retrievers.py
data_ingestion/retrievers/knowledge_graph_retrievers.py

**Tests**
The test files:

1. tests tests/vector_store_isolation_test.py
2. tests/knowledge_graph_isolation_test.py
3. tests/database_isolation_test.py

provide ingestion and retrieval tests for each storage target in isolation.

**Your Tasks**
Based on a clear understanding of all this context, I want to design and implement an End-to-End test to validate that the data ingestion and retrieval needs of the Team Assistant are met.

**Study these files:**:

And the following relevant files:

1. data_ingestion/managers/vector_store_manager.py
2. data_ingestion/managers/database_manager.py
3. data_ingestion/managers/knowledge_graph_manager.py
4. data_ingestion/ingestors/vector_store_ingestor.py
5. data_ingestion/ingestors/database_ingestor.py
6. data_ingestion/ingestors/knowledge_graph_ingestor.py
7. data_ingestion/retrievers/vector_store_retriever.py
8. data_ingestion/retrievers/database_retriever.py
9. data_ingestion/retrievers/knowledge_graph_retriever.py
