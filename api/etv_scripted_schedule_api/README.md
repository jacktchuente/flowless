# etv_scripted_schedule_api

Client Python minimal pour piloter l'API **ErsatzTV scripted-schedule** avec `requests`.

## Installation locale

```bash
pip install -e .
```

## Exemple d'utilisation

```python
from etv_scripted_schedule_api import (
    ScriptedScheduleClient,
    ContentShow,
    ControlWaitUntil,
    PlayoutCount,
)

client = ScriptedScheduleClient(
    host_url="http://localhost:8409",
    build_id="00000000-0000-0000-0000-000000000000",
)

# Déclarer un show comme contenu disponible
client.add_show(ContentShow(
    key="simpsons",
    guids={"jellyfin": "SHOW_GUID_HERE"},
    order="chronological",
))

# Avancer la timeline jusqu'à 20:00, puis ajouter 1 épisode
ctx = client.wait_until(ControlWaitUntil(when="20:00", tomorrow=True))
ctx = client.add_count(PlayoutCount(content="simpsons", count=1))

print(ctx.currentTime, ctx.finishTime)
```

## Notes

- Les modèles utilisent les noms JSON de la doc OpenAPI (`customTitle`, `disableWatermarks`, etc.) afin que `to_dict()` retourne directement un payload valide.
- Chaque méthode accepte soit un objet modèle, soit un `dict` Python.
- Chaque méthode accepte aussi `params={...}` pour d'éventuels query params, même si la spec fournie n'en documente pas.
- `ENDPOINTS` expose une représentation typée des endpoints avec le modèle de payload et de réponse attendu.

## Endpoints couverts

- `get_context() -> PlayoutContext`
- `add_collection(ContentCollection) -> None`
- `add_marathon(ContentMarathon) -> None`
- `add_multi_collection(ContentMultiCollection) -> None`
- `add_playlist(ContentPlaylist) -> None`
- `create_playlist(ContentCreatePlaylist) -> None`
- `add_search(ContentSearch) -> None`
- `add_smart_collection(ContentSmartCollection) -> None`
- `add_show(ContentShow) -> None`
- `add_all(ContentAll) -> PlayoutContext`
- `add_count(PlayoutCount) -> PlayoutContext`
- `add_duration(PlayoutDuration) -> PlayoutContext`
- `pad_to_next(PlayoutPadToNext) -> PlayoutContext`
- `pad_until(PlayoutPadUntil) -> PlayoutContext`
- `pad_until_exact(PlayoutPadUntilExact) -> PlayoutContext`
- `peek_next(content) -> PeekItemDuration`
- `start_epg_group(ControlStartEpgGroup | dict | None) -> None`
- `stop_epg_group() -> None`
- `graphics_on(ControlGraphicsOn) -> None`
- `graphics_off(ControlGraphicsOff | dict | None) -> None`
- `watermark_on(ControlWatermarkOn) -> None`
- `watermark_off(ControlWatermarkOff | dict | None) -> None`
- `pre_roll_on(ControlPreRollOn) -> None`
- `pre_roll_off() -> None`
- `skip_items(ControlSkipItems) -> None`
- `skip_to_item(ControlSkipToItem) -> None`
- `wait_until_exact(ControlWaitUntilExact) -> PlayoutContext`
- `wait_until(ControlWaitUntil) -> PlayoutContext`
