# Pose fixtures

`kras.pdb` and `kras_ref_ligand.sdf` are the KRAS example from
[LPDI-EPFL/lddm](https://github.com/LPDI-EPFL/lddm) (MIT), commit `309ab66`.
The ligand is the crystal pose from PDB 8AZR — it passes all 21 PoseBusters
checks, which is what makes it a usable positive control.

`kras_mixed_poses.sdf` is generated from it as a negative control for
`ligand_pose_gate`: pose 0 is the crystal pose, pose 1 is the same molecule
translated +40 Å (out of the pocket), pose 2 has every coordinate scaled by
0.4 (collapsed bond lengths). A gate that passes any of 1 or 2 is not checking.
