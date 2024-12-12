How It Works
============

The `rocrate-validator` package is designed to validate RO-Crate metadata files against
predefined profiles. The validation process ensures that the metadata conforms to the
expected structure and content as defined by the selected profile.

Validation Process
------------------

1. **Profile Selection**: 
    The user can always specify (via CLI or API) which profile to use
    for validation. If the user does not specify a profile, the system will attempt to detect
    the most appropriate profile based on the `conformsTo` property of the RO-Crate. This
    property indicates which profile the RO-Crate claims to conform to.

2. **Profile Matching**:

    - If a precise match is found for the `conformsTo` property, that profile is selected
      for validation.

    - If no precise match is found, the system will:

      - **Interactive Mode:** the system will prompt the user to select a profile from the list of candidate profiles if interactive mode is enabled (available only through the CLI)

      - **Non-Interactive Mode:** the system will use all candidate profiles for validation if interactive mode is not enabled. If no suitable profile is found, the system will use the base `ro-crate` profile as a fallback.

3. **Profile Versioning**:
    - If the user does not specify a version of the profile, the validator will default to
      using the latest available version of the profile for validation.

.. note::
    The profile version is included in its identifier, allowing the validator to
    accurately distinguish profiles and their versions. For instance, the identifier
    for the `ro-crate` profile version **1.0** is `ro-crate-1.0`, while the profile name
    without a version is simply `ro-crate`.

By following this process, the `rocrate-validator` ensures that the RO-Crate metadata is
validated against the most suitable profile, providing flexibility in
handling different versions and profiles.

