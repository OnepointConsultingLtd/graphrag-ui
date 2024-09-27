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
