# CS3SMOS v300 sample files

Anonymous FTP source (unencrypted):

`ftp://ftp.awi.de/sea_ice/product/cryosat2_smos/v300/nh/`

These retrospective (`processing_mode = "r"`) files were downloaded for an
initial comparison with IS2SMGPSIT-V1. Each file represents a centred seven-day
analysis on the 12.5 km Northern Hemisphere EASE-Grid 2.0 (EPSG:6931).

| Analysis window | Centre time | Size (bytes) | SHA-256 |
|---|---|---:|---|
| 2019-10-22--2019-10-28 | 2019-10-25 12:00 UTC | 9,469,667 | `0b9fdb5b3ebfcb089421c5278380f861c7cccf520ccab72b4bc70c0bd1d56f55` |
| 2020-03-12--2020-03-18 | 2020-03-15 12:00 UTC | 10,332,685 | `e7edb13263e51d73f49035c6fa6103e6b1aed12a68262a9dc9704b0f9e163cb3` |

The files contain `sea_ice_thickness`, `sea_ice_thickness_uncertainty`,
`sea_ice_concentration`, `status_flag`, `quality_flag`, latitude/longitude and
projected coordinates. The quality flag distinguishes combined
altimetry--radiometry, altimetry-only, radiometry-only, interpolated and
no-sea-ice cells.
