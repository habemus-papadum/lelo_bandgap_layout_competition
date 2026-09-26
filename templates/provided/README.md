# Provided-track parts tray

`LELOTEMP_BIAS_IBP.mag` contains all 125 electrical tile instances from the fixed
schematic, sorted by type into a spaced grid. It has no inter-cell wiring. This
grid is a parts tray, not a suggested analog floorplan. Internal tile geometry is
unchanged. The eleven top-level ports are unattached placeholders to the left.

Open this directory with `uv run bandgap magic PATH/TO/THIS/DIRECTORY` from the
competition checkout. The helper expands the cells and fits the whole drawing
automatically. When opening Magic directly, use `select top cell`, `expand`,
`select clear`, and `view` in its console to get the same display.
The project's Magic setup supplies the tile and PDK search paths; no copies of
library cells are needed in your entry.

- Place and orient the cells to implement the fixed schematic. `inventory.csv`
  maps each instance to its schematic hierarchy path and starting coordinates
  (0.005 micrometers per unit). Names join hierarchy levels with `__`.
- Connect terminals using the canonical schematic and cell catalog. Diode
  connections are deliberately left for you to route; ordinary transistor tiles
  are used instead of preconnected `D` variants. Preserve all modeled filler
  transistors and their rail connections.
- `tap_palette.mag` contains one sample of each of the ten physical tap types.
  It is a separate drawing, not a child of the circuit. Open it by file path to
  inspect the choices. Add the appropriate taps to your circuit using their
  library cell names; place, duplicate and connect them to suit your final
  assembly. This palette is not a prescribed tap count. Follow the cell catalog's
  stack/abutment guidance; bipolar substrate contacts also need attention.
- Route power, bulk and signal connections, then move the eleven top-level ports
  onto real conductors. A shared substrate is not a substitute for substrate
  contacts and routing. The global substrate used by extraction is not a drawn
  connection between the pieces.
- Run DRC and LVS during development. The unwired starter intentionally fails
  circuit LVS. Any initial DRC result does not establish a complete design or
  sufficient well/substrate ties. Read `docs/starter-design.md` in the competition
  checkout for measured checks and known initial conditions.

`provenance.json` records the source, cell hashes, counts and painted bounds used
to generate the tray. These and the inventory describe the starting point; they
are not evaluator inputs and do not need updating as you move cells. The tap
palette is not included in grading unless you instantiate it in the circuit
(do not instantiate the entire palette).

The generator uses the bundled PDK's bipolar geometry. An alternative PDK may
have different bounds or extraction behavior and requires its own checks.
