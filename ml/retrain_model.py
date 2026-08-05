"""
Documented retraining entrypoint.

Initially, the ML Anomaly Detector is trained on synthetic data
(synthetic_generator.py -> train_model.py). Once the platform has
accumulated real transaction history, retraining is the same process
against the same database - just re-run this after enough real activity
has occurred:

    ..\\.venv\\Scripts\\python.exe ..\\ml\\retrain_model.py

This is a thin wrapper around train_model.py so the retraining path is
explicit and discoverable, per the plan; the two are intentionally kept
in sync since retraining is *not* a different pipeline, just a later run
of the same one on more/different data.
"""
from train_model import main

if __name__ == "__main__":
    main()
