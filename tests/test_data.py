import pandas as pd
import pytest

from recommender.config import MODEL_FEATURES
from recommender.data import REQUIRED_COLUMNS, clean, load_clean, load_raw, validate


def make_track(track_id, name="Song", artists="Artist", genre="pop", popularity=50):
    row = dict.fromkeys(MODEL_FEATURES, 0.5)
    row.update(
        track_id=track_id,
        track_name=name,
        artists=artists,
        album_name="Album",
        track_genre=genre,
        popularity=popularity,
    )
    return row


def test_clean_removes_rows_with_nulls():
    df = pd.DataFrame([make_track("a", name="One"), make_track("b", name=None)])

    assert clean(df)["track_id"].tolist() == ["a"]


def test_clean_removes_rows_with_zero_tempo():
    silent = make_track("b", name="Noise")
    silent["tempo"] = 0
    df = pd.DataFrame([make_track("a", name="One"), silent])

    assert clean(df)["track_id"].tolist() == ["a"]


def test_clean_keeps_tempo_column():
    assert "tempo" in clean(pd.DataFrame([make_track("a")])).columns


def test_clean_removes_same_track_id_in_several_genres():
    df = pd.DataFrame([make_track("a", genre="pop"), make_track("a", genre="k-pop")])

    assert len(clean(df)) == 1


def test_clean_removes_same_song_with_other_track_id_and_keeps_most_popular():
    df = pd.DataFrame(
        [
            make_track("single", name="Song ", popularity=30),
            make_track("album", name="SONG", popularity=80),
        ]
    )

    assert clean(df)["track_id"].tolist() == ["album"]


def test_clean_keeps_songs_with_same_name_by_other_artist():
    df = pd.DataFrame([make_track("a", artists="One"), make_track("b", artists="Two")])

    assert len(clean(df)) == 2


def test_clean_uses_most_frequent_macro_genre_of_the_song():
    df = pd.DataFrame(
        [
            make_track("a", genre="anime", popularity=90),
            make_track("a", genre="rock", popularity=10),
            make_track("a", genre="punk", popularity=10),
        ]
    )

    assert clean(df)["macro_genre"].tolist() == ["rock"]


def test_clean_result_does_not_depend_on_row_order():
    rows = [make_track("a", popularity=50), make_track("b", name="Other", popularity=50)]

    pd.testing.assert_frame_equal(clean(pd.DataFrame(rows)), clean(pd.DataFrame(rows[::-1])))


def test_load_raw_reads_csv_with_index_column(tmp_path):
    path = tmp_path / "dataset.csv"
    pd.DataFrame([make_track("a")]).to_csv(path)

    assert set(REQUIRED_COLUMNS) <= set(load_raw(path).columns)


def test_load_raw_fails_when_column_is_missing(tmp_path):
    path = tmp_path / "dataset.csv"
    pd.DataFrame([make_track("a")]).drop(columns="energy").to_csv(path)

    with pytest.raises(ValueError, match="energy"):
        load_raw(path)


def clean_tracks(**changes):
    rows = [make_track("a", name="One"), make_track("b", name="Two")]
    df = clean(pd.DataFrame(rows).assign(tempo=120.0, loudness=-8.0, mode=1))
    return df.assign(**changes)


def test_validate_accepts_clean_data():
    validate(clean_tracks())


def test_validate_reports_values_out_of_range():
    with pytest.raises(ValueError, match=r"energy: 2 valores fuera de \[0.0, 1.0\]"):
        validate(clean_tracks(energy=1.5))


def test_validate_reports_every_problem_at_once():
    with pytest.raises(ValueError, match="tempo.*popularity"):
        validate(clean_tracks(tempo=0, popularity=101))


def test_validate_reports_nulls():
    with pytest.raises(ValueError, match="artists: 2 nulos"):
        validate(clean_tracks(artists=None))


def test_validate_reports_repeated_track_id():
    with pytest.raises(ValueError, match="track_id: 1 repetidos"):
        validate(clean_tracks(track_id="a"))


def test_validate_reports_missing_macro_genre_column():
    with pytest.raises(ValueError, match="macro_genre"):
        validate(clean_tracks().drop(columns="macro_genre"))


def test_validate_rejects_empty_dataset():
    with pytest.raises(ValueError, match="vacío"):
        validate(clean_tracks().iloc[0:0])


def test_load_clean_validates(tmp_path):
    path = tmp_path / "clean.csv"
    clean_tracks(valence=-1).to_csv(path, index=False)

    with pytest.raises(ValueError, match="valence"):
        load_clean(path)
