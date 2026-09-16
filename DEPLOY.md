# Deploying to Streamlit Community Cloud

The application is designed for Streamlit Community Cloud. The generated data
is committed, so deployment only installs the small runtime dependency set and
starts `app.py`.

Current deployment: [NFL Game Predictor](https://nfl-game-predictor-snhqz6kcp4w37t87y4kgnk.streamlit.app/)

## Deploy

1. Push the repository to GitHub.
2. Sign in at [share.streamlit.io](https://share.streamlit.io).
3. Choose **Create app** and select this repository.
4. Select the `main` branch.
5. Set the main file path to `app.py`.
6. Deploy.

Streamlit reads `requirements.txt` automatically. No database, separate server,
secrets, or custom startup command is required.

## Verify before publishing

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest
streamlit run app.py
```

Confirm that:

- the dashboard opens without an artifact-contract error
- changing teams updates the logo, record, schedule, and form metrics
- league standings and weekly predictions render
- model metrics match `data/model_info.json`
- `.venv/`, caches, IDE metadata, and secrets are not committed

## Refresh predictions

During the season, rebuild locally:

```bash
source .venv/bin/activate
python python/build_data.py
python -m pytest
```

Review and commit the refreshed files under `data/`, then push them. Streamlit
Community Cloud redeploys from the new commit and reloads the artifacts.

## Troubleshooting

If deployment reports missing files, confirm that all five generated artifacts
and `data/data_contract.json` are present in GitHub. If dependency installation
fails, check that Streamlit is using a supported Python version and review the
first package error in the build log.
