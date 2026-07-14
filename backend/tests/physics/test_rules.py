from app.physics.rules import compute_damage, update_relationship, RELATIONSHIP_CHANGE

def test_damage_reduces_health():
    new_health = compute_damage(100, severity="moderate")
    assert new_health < 100
    assert new_health >= 50

def test_light_damage():
    new_health = compute_damage(100, severity="light")
    assert new_health == 90

def test_severe_damage():
    new_health = compute_damage(100, severity="severe")
    assert new_health <= 50

def test_relationship_decrease_on_conflict():
    new_affinity = update_relationship(0.0, action_type="conflict")
    assert new_affinity < 0.0

def test_relationship_increase_on_cooperation():
    new_affinity = update_relationship(0.0, action_type="dialogue", positive=True)
    assert new_affinity > 0.0
