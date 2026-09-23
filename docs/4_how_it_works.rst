..
    Copyright (c) 2024-2026 CRS4

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

How It Works
============

The `rocrate-validator` is designed to validate RO-Crates against predefined
*validation profiles*. A validation profile is a set of validation rules, or
*checks*, which are applied to the RO-Crate.  If the RO-Crate conforms to all
the rules, then it is deemed *valid*; otherwise, errors will be generated for
each rule that failed to validate.

Non-conformance to a rule will result in an *issue*.  On the CLI, issues will
be presented as error messages, with references to the specific rule which
triggered the error. Note that multiple rules may have the same error message,
which can result in output with apparently duplicate errors.

`rocrate-validator` is limited to validating conformance to RO-Crate
profiles for which validation rules have been implemented.  In the absence of
any matching validation profiles, `rocrate-validator` may return an error or
request the user to manually select a validation profile to apply.

Validation profiles can be related by inheritance -- i.e., where one validation
profile extends another one. For instance, Workflow Testing RO-Crate extends Workflow RO-Crate.


Validation lifecycle and prepared profiles
------------------------------------------

An instance of :class:`rocrate_validator.models.Validator` keeps the profile
preparation state used by its validation runs.  This state contains the resolved
profile chain and the profile objects which lazily own requirements and SHACL
shape registries.  Repeated calls on the same validator can therefore reuse
parsed profile artifacts instead of loading them again.

Crate-specific state is never part of the prepared profile state.  Every run
still creates a new validation context, data graph, result, and SHACL execution
context, so inference, SHACL rules, violations, and skipped checks cannot leak
from one run into another.  Validation statistics use the same prepared profile
instances as their owning validation context rather than loading a second copy.

Profile artifacts can contain relative IRIs. For the ordinary case where the
effective JSON-LD base is the crate public ID, profiles are prepared once using
a stable internal base. Each SHACL run copies the much smaller prepared shapes
and ontology graphs, rebases their relative data terms to the current crate,
and preserves structural shape identifiers. The crate data graph itself is
never rewritten. This permits different crate locations to share preparation
without leaking their public IDs into one another.

An explicit JSON-LD ``@base`` different from the crate public ID retains a
base-specific prepared plan. This conservative boundary preserves the two RDF
spaces used by existing profiles rather than collapsing them during rebasing.


Validation profile selection
----------------------------

* **Automatic Profile Matching** (default):
  By default, `rocrate-validator` will attempt to select the correct validation
  profiles for the input RO-Crate based on the `conformsTo` property of the Root Data Entity.

    - If a precise match is found for the `conformsTo` property, that profile is selected
      for validation.

    - If no precise match is found:

      - in **Interactive Mode:** (available only through the CLI) the system
        will prompt the user to select a profile from the list of
        profiles to which the RO-Crate conforms;

      - in **Non-Interactive Mode:** the system will validate against all profiles
        to which the RO-Crate conforms, and for which validation rules are available.
        In all cases, input RO-Crates are validated against the base `ro-crate` profile.

* **Profile Versions**:
    - It may happen that the RO-Crate profile version to which the input
      RO-Crate `conformsTo` does not match the version of the implemented
      validation profile. In this case, the validator will validate against the
      *highest available version* of the profile that is lower than the one
      requested. Thus, the validator will avoid applying a validation profile
      that is newer than the `conformsTo` profile.  This behaviour can be
      overridden by manually selecting the desired validation profile (see below).

  .. note::
      Profile versions are identified by matching the trailing version number
      in the profile identifier, if present. For instance, the identifier for
      the `ro-crate` profile version **1.0** is `ro-crate-1.0`, while the
      profile name without a version is simply `ro-crate`.

* **Manual Profile Selection**:
    The user can always override the automatic selection of validation profiles
    by specifying (via CLI or API) which profile to use.
