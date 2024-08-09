# rocrate-validator

[![main workflow](https://github.com/crs4/rocrate-validator/actions/workflows/testing.yaml/badge.svg)](https://github.com/crs4/rocrate-validator/actions/workflows/testing.yaml) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

<!-- [![Build Status](https://repolab.crs4.it/lifemonitor/rocrate-validator/badges/develop/pipeline.svg)](https://repolab.crs4.it/lifemonitor/rocrate-validator/-/pipelines?page=1&scope=branches&ref=develop) -->

<!-- [![PyPI version](https://badge.fury.io/py/rocrate-validator.svg)](https://badge.fury.io/py/rocrate-validator) -->

<!-- [![codecov](https://codecov.io/gh/crs4/rocrate-validator/branch/main/graph/badge.svg?token=3ZQZQZQZQZ)](https://codecov.io/gh/crs4/rocrate-validator) -->

A Python package to validate [ROCrate](https://researchobject.github.io/ro-crate/) packages.

## Setup

Follow these steps to setup the project:

1. **Clone the repository**

```bash
git clone https://github.com/crs4/rocrate-validator.git
cd rocrate-validator
```

2. **Setup a Python virtual environment (optional)**

Setup a Python virtual environment using `venv`:

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

### using Poetry

Run the validator using the following command:

```bash
poetry run rocrate-validator validate <path_to_rocrate>
```

Replace `<path_to_rocrate>` with the path to the ROCrate you want to validate.

Type `poetry run rocrate-validator --help` for more information.

### using the installed package on your virtual environment

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Then, run the validator using the following command:

```bash
rocrate-validator validate <path_to_rocrate>
```

Replace `<path_to_rocrate>` with the path to the ROCrate you want to validate.

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

<img alt="Co-funded by the EU"
    src="https://raw.githubusercontent.com/crs4/rocrate-validator/develop/docs/img/eu-logo/EN_Co-fundedbytheEU_RGB_POS.png"
    width="250" align="right"/>

-   the [BY-COVID](https://by-covid.org/) project (HORIZON Europe grant agreement number 101046203);
-   the [LIFEMap](https://www.thelifemap.it/) project, funded by the Italian Ministry of Health (Piano Operative Salute, Trajectory 3).

