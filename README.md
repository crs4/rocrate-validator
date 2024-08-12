# rocrate-validator

[![main workflow](https://github.com/crs4/rocrate-validator/actions/workflows/testing.yaml/badge.svg)](https://github.com/crs4/rocrate-validator/actions/workflows/testing.yaml) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

<!-- [![Build Status](https://repolab.crs4.it/lifemonitor/rocrate-validator/badges/develop/pipeline.svg)](https://repolab.crs4.it/lifemonitor/rocrate-validator/-/pipelines?page=1&scope=branches&ref=develop) -->

<!-- [![PyPI version](https://badge.fury.io/py/rocrate-validator.svg)](https://badge.fury.io/py/rocrate-validator) -->

<!-- [![codecov](https://codecov.io/gh/crs4/rocrate-validator/branch/main/graph/badge.svg?token=3ZQZQZQZQZ)](https://codecov.io/gh/crs4/rocrate-validator) -->

A Python package to validate [RO-Crate](https://researchobject.github.io/ro-crate/) packages.

* Supports CLI-based validation as well as programmatic validation (so it can
  easily be used by Python code).
* Implements an extensible validation framework to which new RO-Crate profiles
  can be added.  Validation is based on SHACL shapes and Python code.
* Currently, validations for the following profiles are implemented: RO-Crate
  (base profile), [Workflow
  RO-Crate](https://www.researchobject.org/ro-crate/specification/1.1/workflows.html),
  [Process Run
  Crate](https://www.researchobject.org/workflow-run-crate/profiles/0.1/process_run_crate.html).
  More are being implemented.

**Note**: this software is still work in progress. Feel free to try it out,
report positive and negative feedback.  Do send a note (e.g., by opening an
Issue) before starting to develop patches you would like to contribute.  The
implementation of validation code for additional RO-Crate profiles would be
particularly welcome.

## Setup

Follow these steps to set up the project:

1. **Clone the repository**

```bash
git clone https://github.com/crs4/rocrate-validator.git
cd rocrate-validator
```

2. **Set up a Python virtual environment (optional)**

Set up a Python virtual environment using `venv`:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Or using `virtualenv`:

```bash
virtualenv .venv
source .venv/bin/activate
```

This step, while optional, is recommended for isolating your project dependencies. If skipped, Poetry will automatically create a virtual environment for you.

3. **Install the project using Poetry**

Ensure you have Poetry installed. If not, follow the instructions [here](https://python-poetry.org/docs/#installation). Then, install the project:

```bash
poetry install
```

## Usage

After installation, you can use the main command `rocrate-validator` to validate ROCrates.

### Using Poetry

Run the validator using the following command:

```bash
poetry run rocrate-validator validate <path_to_rocrate>
```

Replace `<path_to_rocrate>` with the path to the RO-Crate you want to validate.

Type `poetry run rocrate-validator --help` for more information.

### Using the installed package on your virtual environment

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Then, run the validator using the following command:

```bash
rocrate-validator validate <path_to_rocrate>
```

Replace `<path_to_rocrate>` with the path to the RO-Crate you want to validate.

Type `rocrate-validator --help` for more information.

## Running the tests

To run the tests, use the following command:

```bash
poetry run pytest
```

<!-- ## Contributing

Contributions are welcome! Please read our [contributing guidelines](CONTRIBUTING.md) for details. -->

## License

This project is licensed under the terms of the Apache License 2.0. See the
[LICENSE](LICENSE) file for details.

## Acknowledgements

This work has been partially funded by the following sources:

* the [BY-COVID](https://by-covid.org/) project (HORIZON Europe grant agreement number 101046203);
* the [LIFEMap](https://www.thelifemap.it/) project, funded by the Italian Ministry of Health (Piano Operative Salute, Trajectory 3).

<img alt="Co-funded by the EU"
    src="https://raw.githubusercontent.com/crs4/rocrate-validator/develop/docs/img/eu-logo/EN_Co-fundedbytheEU_RGB_POS.png"
    width="250" align="right"/>
