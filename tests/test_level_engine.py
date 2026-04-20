from app.services.level_engine import compute_levels


def test_compute_levels():
    result = compute_levels(2500, 2400, 2450)
    assert result['eq'] == 2450
