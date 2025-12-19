Validation Profiles
===================

The system comes with a set of **predefined validation profiles** that are loaded 
automatically when the application starts (see `supported profiles <../#features>`_). 
These profiles define the standard rules and checks that are applied during RO-Crate validation.

Additional Profiles
-------------------

You can **extend or override** the predefined validation profiles by specifying 
the path to additional profiles using the ``--extra-profiles-path`` option on the command line.

CLI Usage
^^^^^^^^^

.. code-block:: bash

    rocrate-validator validate --extra-profiles-path /path/to/additional/profiles <other_options> <path_to_rocrate>

API Usage
^^^^^^^^^^^^^

.. code-block:: python

    # Import the `services` and `models` module from the rocrate_validator package
    from rocrate_validator import services, models

    # Create an instance of `ValidationSettings` class to configure the validation
    settings = services.ValidationSettings(
        # ... value for other settings ...

        # Define the path to additional validation profiles
        extra_profiles_path="/path/to/additional/profiles"  # Path to additional validation profiles
    )

    # Call the validation service with the settings
    result = services.validate(settings)

    # process the validation result
    ...


Behavior
^^^^^^^^

* Profiles provided via ``--extra-profiles-path`` are **loaded in addition to** the system’s predefined profiles.  
* If an additional profile has the **same name** as a predefined profile, the additional profile **overrides** the predefined one.  

This mechanism allows you to:

* **Add new custom validation profiles** to implement project-specific checks.  
* **Modify existing profiles** without altering the system’s predefined configuration files.  
* **Maintain a clear separation** between standard validation logic and project-specific customizations.  
