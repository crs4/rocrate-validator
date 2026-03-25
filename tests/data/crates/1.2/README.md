# RO-Crate 1.2 Detached examples

This folder contains example Detached RO-Crate metadata files for 1.2. Each example is a metadata-only JSON-LD file that references remote data entities.

## Examples
- `detached-basic/basic-ro-crate-metadata.json`
  - Minimal detached RO-Crate with a single remote file.
- `detached-multi/multi-ro-crate-metadata.json`
  - Detached RO-Crate with multiple remote files and a remote dataset.
- `detached-with-profile/profiled-ro-crate-metadata.json`
  - Detached RO-Crate that declares conformance to an additional profile.

## Notes
- Detached RO-Crates have no local payload; all data entities use absolute URIs.
- The metadata document uses the 1.2 context by reference.
