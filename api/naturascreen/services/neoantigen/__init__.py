"""Neoantigen channel: MHC class I epitope generation, MHCflurry presentation
prediction, persistence, and the scoring adapter.

Importing this package is cheap and dependency-free — MHCflurry / TensorFlow are
imported lazily inside ``predictor.predict_presentation`` only when a real
prediction is requested, so the pipeline can import the adapter unconditionally.
"""
