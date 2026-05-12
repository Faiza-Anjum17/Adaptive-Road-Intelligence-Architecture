# ARIA Smart City Traffic AI

ARIA is a smart-city traffic orchestration demo that combines route search, policy checks, ANN-based priority prediction, and signal allocation into a single decision pipeline.

The project includes two UIs:

- `streamlit_app.py` for Streamlit Cloud deployment
- `gradio_ui.py` for the original Gradio interface

## Features

- Dispatch request form for emergency and civilian scenarios
- Route generation with live graph and Folium map views
- ANN-based priority classification
- Policy / knowledge-base decision layer
- CSP-based signal allocation
- Request history table and request log output

## Local Run

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the Streamlit app:

```bash
streamlit run streamlit_app.py
```

## Deploy to Streamlit Cloud

1. Push this repository to GitHub.
2. In Streamlit Cloud, create a new app from the repository.
3. Set the main file path to `streamlit_app.py`.
4. Let Streamlit install the dependencies from `requirements.txt`.

If Streamlit Cloud asks for a Python file entry point, choose `streamlit_app.py` rather than `main.py`.

## Notes

- The ANN models are initialized through `train_priority_models()` and cached by Streamlit to avoid retraining on every interaction.
- The app writes request history to `logs/request_log.json`. On Streamlit Cloud, this file is useful for session history but should not be treated as durable storage.
- If you want the Gradio version instead, run `python gradio_ui.py` locally.

## Project Layout

- `streamlit_app.py` - Streamlit UI and cloud entry point
- `gradio_ui.py` - Original Gradio UI
- `main.py` - Console simulation entry point
- `modules/` - routing, ANN, search, policy, and signal logic
- `data/` - graph and training data
- `logs/` - generated map HTML and request logs
