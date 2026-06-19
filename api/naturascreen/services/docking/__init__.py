"""AutoDock Vina docking adapter and curated cancer-target registry.

The adapter (``adapter.score``) is the binding sub-score channel of the scoring
pipeline. It docks a compound into a curated search box on a protein target and
returns the best Vina affinity (kcal/mol, more negative = stronger). It refuses
to run — raising ``AdapterUnavailable`` — whenever the box, the Vina binary, or
the prepared receptor is not provisioned, because a wrong or absent box produces
confident garbage. No tool/data, no number.

Heavy chemistry libraries (vina, meeko, rdkit) are imported lazily inside the
functions that use them, so importing this package never requires them; the
pipeline imports adapter modules unconditionally.
"""
