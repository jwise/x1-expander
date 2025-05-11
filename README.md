# X1Plus Expander

This repository contains hardware development files for the X1Plus Expander,
[available-ish for purchase at Crowd
Supply](https://www.crowdsupply.com/accelerated-tech/x1plus-expander). 
Printer-side software to interface with these boards lives in the [X1Plus
repository](https://github.com/x1plus/x1plus).

If you have just purchased an Expander, you probably want to [read the
getting started guide](doc/getting-started.md)!

Each part has its own directory in this repository.  Part numbers always
begin with "X1P", are followed by three digits to identify the part, and
have a three-character revision number: a letter to identify
form/fit/function-incompatible revisions, and two digits to identify
FFF-compatible revisions.  Put together, a part and revision number looks
like "X1P-002-C02", to identify the an X1Plus Expansion Board mainboard, the
third FFF-incompatible revision, and the second FFF-compatible revision of
the X1P-002-C family.

This repository contains the following parts.  (Descriptions below may not
be representative of marketing names.)

 * [X1P-001](x1p-001/): wiring harness to connect X1P-002 to the printer
 * [X1P-002](x1p-002/): X1Plus Expander mainboard
 * [X1P-003](x1p-003/): manufacturing test harness for X1P-002
 * [X1P-004](x1p-004/): LED strip 3.3V->5V level shifter plugin
 * [X1P-005](x1p-005/): Andon board plugin
 * [X1P-006](x1p-006/): 2.5mm camera shutter release plugin
 * X1P-100 is a part number reserved for a bundle assembly of X1P-001,
   X1P-002, and X1P-800.
 * [X1P-800](x1p-800/): plastics for X1P-002

Ideally, each known version of each of these parts has its own git tag and
GitHub release with manufacturing data.  (Ideally.)

Also in this repository:

 * [utils/](utils/): software useful in manufacturing or bringup of X1P-*
   hardware
 * [doc/](doc/): documentation associated with X1P-* hardware
 * [fw/](fw/): firmware for the RP2040 on X1P-002-C series boards