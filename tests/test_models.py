
import pytest

from rocrate_validator.models import (RequirementLevel, RequirementType,
                                      Severity)


def test_severity_ordering():
    assert Severity.OPTIONAL < Severity.RECOMMENDED
    assert Severity.RECOMMENDED > Severity.OPTIONAL
    assert Severity.RECOMMENDED < Severity.REQUIRED
    assert Severity.OPTIONAL < Severity.REQUIRED
    assert Severity.OPTIONAL == Severity.OPTIONAL
    assert Severity.RECOMMENDED <= Severity.REQUIRED
    assert Severity.RECOMMENDED >= Severity.OPTIONAL


def test_requirement_type_ordering():
    may = RequirementType('MAY', Severity.OPTIONAL)
    should = RequirementType('SHOULD', Severity.RECOMMENDED)
    assert may < should
    assert should > may
    assert should != may
    assert may == may
    assert may != 1
    with pytest.raises(TypeError):
        _ = may > 1


def test_requirement_type_basics():
    may = RequirementType('MAY', Severity.OPTIONAL)
    assert str(may) == "MAY"
    assert int(may) == Severity.OPTIONAL.value


def test_requirement_levels():
    assert RequirementLevel.get('may') == RequirementLevel.MAY.value

    # Test ordering
    assert RequirementLevel.MAY < RequirementLevel.SHOULD
    assert RequirementLevel.SHOULD > RequirementLevel.MAY
    assert RequirementLevel.SHOULD != RequirementLevel.MAY
    assert RequirementLevel.MAY == RequirementLevel.MAY

    all_levels = RequirementLevel.all()
    assert isinstance(all_levels, dict)
    assert 10 == len(all_levels)
    # Test a few of the keys
    assert 'MAY' in all_levels
    assert 'SHOULD_NOT' in all_levels
    assert 'RECOMMENDED' in all_levels
    assert 'REQUIRED' in all_levels
