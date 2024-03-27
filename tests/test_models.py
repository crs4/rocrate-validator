
import pytest

from rocrate_validator.models import (LevelCollection, RequirementLevel,
                                      Severity)


def test_severity_ordering():
    assert Severity.OPTIONAL < Severity.RECOMMENDED
    assert Severity.RECOMMENDED > Severity.OPTIONAL
    assert Severity.RECOMMENDED < Severity.REQUIRED
    assert Severity.OPTIONAL < Severity.REQUIRED
    assert Severity.OPTIONAL == Severity.OPTIONAL
    assert Severity.RECOMMENDED <= Severity.REQUIRED
    assert Severity.RECOMMENDED >= Severity.OPTIONAL


def test_level_ordering():
    may = RequirementLevel('MAY', Severity.OPTIONAL)
    should = RequirementLevel('SHOULD', Severity.RECOMMENDED)
    assert may < should
    assert should > may
    assert should != may
    assert may == may
    assert may != 1
    assert may != RequirementLevel('OPTIONAL', Severity.OPTIONAL)
    with pytest.raises(TypeError):
        _ = may > 1


def test_level_basics():
    may = RequirementLevel('MAY', Severity.OPTIONAL)
    assert str(may) == "MAY"
    assert int(may) == Severity.OPTIONAL.value


def test_level_collection():
    assert LevelCollection.get('may') == LevelCollection.MAY

    # Test ordering
    assert LevelCollection.MAY < LevelCollection.SHOULD
    assert LevelCollection.SHOULD > LevelCollection.MAY
    assert LevelCollection.SHOULD != LevelCollection.MAY
    assert LevelCollection.MAY == LevelCollection.MAY

    all_levels = LevelCollection.all()
    assert 10 == len(all_levels)
    level_names = [level.name for level in all_levels]
    # Test a few of the keys
    assert 'MAY' in level_names
    assert 'SHOULD_NOT' in level_names
    assert 'RECOMMENDED' in level_names
    assert 'REQUIRED' in level_names
