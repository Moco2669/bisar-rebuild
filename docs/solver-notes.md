# Solver notes

Read this before changing `src/bisar/engine.py`. Four scratch scripts in the local Temp folder, `shear_kernel.py`, `shear_halfspace.py`, `shear_layers.py`, and `shear_compare.py`, are drafts of the derivation below. The program is the engine. Leave the drafts out of git.

## Slip

The fourth number on a layer record is the reduced compliance ALK, in metres. The compliance used at the interface is AK = ALK (1+ν)/E of the layer that carries the number, which is the layer above the interface. The radial jump in the solver is ur above minus ur below = −AK τ_rz. In `_coefficients` that is the positive `factor * standard` addition on the upper layer's τ_rz weights. The opposite sign was tried and rejected: settlement at the first slip point moved from 5.808e-5 to about 4.77e-5, and xz changed sign. On the recorded case ALK = 10.5 m, which is close to full slip, and τ at that interface is about 2130 Pa.

## Horizontal shear

A uniform horizontal traction is a separate solution from the vertical Love field. It is a Galerkin vector. The x-component is axisymmetric. The z-component varies as cos θ. A finite layer has unknowns A, B, C, D for the x-component and F, H for the part of the z-component that is proportional to depth. The constant part of the z-component is omitted because it repeats the x-component. The half-space keeps A, B, and F. That is 6 unknowns in each finite layer and 3 in the half-space.

Depth is positive downward. On the surface, σ_z is 0, the order-2 part of τ_xz is 0, and the order-0 amplitude of τ_xz is minus the Hankel transform of the applied shear, q a J1(ξ a)/ξ. That minus sign is the one for which the surface-center displacement is (1+ν)(2−ν) q a / E. Direction 0 means +X. Any other direction rotates that frame back onto the fixed axes. The vertical load is solved as before, and this field is added to it.

Displacement continuity rows are multiplied by μ of the top layer times ξ. Without that factor the matrix is ill-conditioned and the small stresses move.

The integral uses the zeros of J1 and 48-point Gauss on each lobe, out to 40 divided by the smaller of the depth and the finite-layer thicknesses. The 24-point rule used for vertical loads left the on-axis shear displacement about 1.3% low, 2.734e-6 instead of 2.771e-6.

The order-2 identity is J2(x)/x = (J1(x)+J3(x))/4. Using 2 in the denominator leaves σ_xx on the shear axis looking right and makes σ_yy and σ_xy wrong.

In the shear frame, with ux0, ux2, and uz the 2μ displacement amplitudes from `_shear_fields` and lap the dilatation potential returned with them, the normal stresses that matched the recorded run are:

- σ_xx: the cos θ J1 amplitude is ν lap − ξ ux0 + (ξ/2) ux2, and the cos 3θ J3 amplitude is −(ξ/2) ux2
- σ_yy: the cos θ J1 amplitude is ν lap + (ξ/2) ux2, and the cos 3θ J3 amplitude is +(ξ/2) ux2
- σ_xy: the sin θ J1 amplitude is −(ξ/2) ux0, and the sin 3θ J3 amplitude is −(ξ/2) ux2
- τ_xz is the order-0 amplitude plus cos 2θ times the order-2 amplitude
- τ_yz is sin 2θ times that same order-2 amplitude

At the recorded point on the Y axis, σ_xy is the difference of two slopes of about 1.5e-6. The solver gives 100.4 Pa and the recorded print is 100.8 Pa. The shear test allows half a pascal on that component. The other components of that run sit inside the usual 0.1% check. Leave the kernel alone over that half pascal.

Surface stresses under a horizontal load are a poor check. The recorded points are at 0.30 m and deeper.

## Recorded files

`DUMMY.INP` and `DUMMY.OUT` are whatever the Windows program calculated last. The shear-load numbers were read from `BISAR3.MDB` after a later slip run replaced `DUMMY`. The fixtures under `tests/fixtures` are the copy that matters. A test of a real report checks that the report parses. It does not hard-code how many positions that file has.
