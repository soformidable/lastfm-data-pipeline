CREATE TABLE IF NOT EXISTS lastfm_scrobbles (
    scrobble_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
    Artist       VARCHAR(255),
    Album        VARCHAR(255),
    Track        VARCHAR(255),
    Date_played  DATE,
    Time_played  TIME,
    Genres       JSON,
    UNIQUE KEY uq_scrobble (Artist, Album, Track, Date_played, Time_played)
);

CREATE TABLE IF NOT EXISTS Last_fm_stats (
    stat_id                INT PRIMARY KEY,
    latest_scrobble_time   DATETIME,
    latest_scrobble_track  VARCHAR(255),
    latest_scrobble_artist VARCHAR(255),
    top_track              VARCHAR(255),
    top_track_count        INT,
    top_artist             VARCHAR(255),
    top_artist_count       INT,
    top_date               DATE,
    top_date_count         INT,
    best_day_of_week       VARCHAR(50),
    best_day_avg           FLOAT,
    saturated_track        VARCHAR(255)
);
