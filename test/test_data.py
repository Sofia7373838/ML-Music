import pandas as pd
import pytest

from recommender.config import MODEL_FEATURES
from recommender.data import REQUIRED_COLUMNS, clean, load_raw


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
