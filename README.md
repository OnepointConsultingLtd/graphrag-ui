# Graph RAG UI

Simple FastHTML based UI for [Graph RAG](https://github.com/microsoft/graphrag).

# Setup

```
conda create -n graphrag-ui python=3.12
conda activate graphrag-ui
# pip install poetry
conda install conda-forge::poetry
poetry install
```

# Running the UI

```
python graphrag_ui/ui/main.py
```

The server typically runs on http://localhost:5001/


# Running Neo4J

```
cd C:\development\playground\rag\graphrag-ui
docker compose up
```

## Checking configuration:

```
docker exec -it neo4j-apoc cat /var/neo4j/lib/plugins/README.txt
```

## Accessing the console:
```
docker exec -it neo4j-apoc bash
```

## Visualizing entities

https://workspace-preview.neo4j.io/workspace/query