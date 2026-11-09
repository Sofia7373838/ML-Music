from recommender.genres import GENRE_TO_MACRO, MACRO_GENRES, UNKNOWN_MACRO_GENRE, to_macro_genre


def test_each_genre_belongs_to_one_macro_genre():
    assert len(GENRE_TO_MACRO) == sum(len(genres) for genres in MACRO_GENRES.values())


def test_related_genres_share_macro_genre():
    assert {to_macro_genre(g) for g in ["pop", "indie-pop", "k-pop"]} == {"pop"}


def test_unmapped_genre_is_marked_as_unknown():
    assert to_macro_genre("genero-inventado") == UNKNOWN_MACRO_GENRE