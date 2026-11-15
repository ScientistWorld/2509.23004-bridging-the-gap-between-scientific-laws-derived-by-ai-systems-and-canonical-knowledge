# Data Assets

`systems_and_phenomena/` holds the twelve polynomial benchmark theories published
with the paper (https://github.com/IBM/AI-Noether, folder
`systems_and_phenomena`; `scripts/download.sh` re-fetches them). Each
`system.txt` lists variables, axioms, measured variables and target
polynomial(s); `system_noise_*.txt` are the upstream noisy-target variants
(unused by the exact gym).

These theories form the visible train slice. `eval/train/build_instances.py`
turns them into anonymized, unit-rescaled abduction instances
(`eval/train/instances.json`). The held-out theories are not stored here.

`systems_mc_train/` holds four larger public extensions of the paper's theories
(authored for this gym, tracked in git), used only by the train slice of the
multiple-consequence experiment; see its README.
