from django.db import models


class MediaSourceType:
    jellyfin = 1


class MediaCategoryType:
    genre = 1
    tag = 2


class MediaNature(models.IntegerChoices):
    FICTION = 1, "fiction"
    DOCUMENTARY = 2, "documentary"
    MUSIC = 3, "music"
    SPORT = 4, "sport"
    NEWS = 5, "news"
    SHOW = 6, "show"
    OTHER = 99, "other"


class MediaContainerKind(models.IntegerChoices):
    STANDALONE_VIDEO = 1, "standalone_video"
    SERIES = 2, "series"
    MUSIC_RELEASE = 3, "music_release"
    MUSIC_VIDEO_RELEASE = 4, "music_video_release"
    OTHER = 99, "other"


class MediaItemKind(models.IntegerChoices):
    VIDEO = 1, "video"
    EPISODE = 2, "episode"
    MUSIC_TRACK = 3, "music_track"
    MUSIC_VIDEO = 4, "music_video"
    OTHER = 99, "other"


class MediaProgrammingRole(models.IntegerChoices):
    MAIN = 1, "main"                 # contenu principal
    TRAILER = 2, "trailer"           # bande-annonce d’un contenu
    PROMO = 3, "promo"               # promo chaîne / promo programme
    AD = 4, "ad"                     # publicité commerciale
    BUMPER = 5, "bumper"             # habillage court
    IDENT = 6, "ident"               # ident chaîne / station ID
    FILLER = 7, "filler"             # contenu de remplissage
    PSA = 8, "psa"                   # message d’intérêt public
    OTHER = 99, "other"

MUSIC_CONTAINER_KINDS = (
    MediaContainerKind.MUSIC_RELEASE,
    MediaContainerKind.MUSIC_VIDEO_RELEASE,
)
