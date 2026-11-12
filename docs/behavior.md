# Behavior

## Bonded centerline

One vertical circular load on four fully bonded layers, with the response asked on the load axis. The recorded case is `tests/fixtures/nrb1.inp`.

## Standard dual wheel

Manual section 10.2. Two vertical wheels of the standard axle, full friction between the layers, and positions between the wheels and under one wheel. Where the same depth lies on an interface, the layer above and the layer below are both reported. The combined response is in the fixed horizontal frame: displacements UX, UY, UZ and normal stresses XX, YY, ZZ. The recorded case is `tests/fixtures/dual.inp`.

## Interface slip

Manual section 10.3. The same four layers and one vertical wheel, with a reduced shear-spring compliance of 10.5 m on the interface under the top layer. That length is 100 times the loaded radius, so the interface is close to full slip. The other interfaces stay bonded. The recorded case is `tests/fixtures/slip.inp`.

## Horizontal shear

The same bonded structure and vertical wheel, plus a 5 kN horizontal load aimed along X. The direction is the compass angle of that force, measured from +X. The vertical pressure and the horizontal traction are added together. The recorded case is `tests/fixtures/shear.inp`.
