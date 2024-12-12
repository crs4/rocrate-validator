How It Works
============

The `ro-crate-validator` package is designed to validate RO-Crate metadata files against
predefined profiles. The validation process ensures that the metadata conforms to the
expected structure and content as defined by the selected profile.

Validation Process
------------------

1. **Profile Detection**: The system attempts to detect the most appropriate profile based
    on the `conformsTo` property of the RO-Crate. This property indicates which profile the
    RO-Crate claims to conform to.

2. **Profile Matching**:
    - If a precise match is found for the `conformsTo` property, that profile is selected
      for validation.
    - If no precise match is found, the system will:
      - **Interactive Mode**: If interactive mode is enabled, the system will prompt the
         user to select a profile from the list of candidate profiles.
      - **Non-Interactive Mode**: If interactive mode is not enabled, the system will use
         all candidate profiles for validation.

3. **Profile Versioning**:
    - If the user does not specify a version of the profile, the system will use the latest
      available version of the profile for validation.

By following this process, the `ro-crate-validator` ensures that the RO-Crate metadata is
validated against the most suitable profile, providing flexibility and robustness in
handling different versions and profiles.

