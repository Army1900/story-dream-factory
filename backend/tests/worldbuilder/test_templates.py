from app.worldbuilder.templates import BUILTIN_TEMPLATES

def test_three_templates():
    assert len(BUILTIN_TEMPLATES) == 3

def test_template_has_genre_and_drafts():
    for t in BUILTIN_TEMPLATES:
        assert t["name"]
        assert t["genre"]
        assert isinstance(t["rules_draft"], list)
        assert isinstance(t["visual_style_draft"], dict)

def test_template_genres_differ():
    genres = [t["genre"] for t in BUILTIN_TEMPLATES]
    assert len(set(genres)) == 3
