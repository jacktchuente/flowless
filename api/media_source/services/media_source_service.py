from media_source.models import MediaSource, MediaCollection
from media_source.services.media_server_services.jellyfin_service import JellyfinService


class MediaSourceService:

    def __init__(self, media_source: MediaSource):
        self.media_source = media_source

    def sync_collection(self):

        founded_collections = JellyfinService(credentials=self.media_source.credentials).get_collections()
        existing_collection = MediaCollection.objects.filter(media_source=self.media_source).values_list(
            "external_id",
            "pk"
        )
        existing_collection_map = {
            collection[0]: collection[1] for collection in existing_collection
        }

        existing_collection_external_ids = [collection[0] for collection in existing_collection]
        new_collection_payload = []
        old_collection_payload = []

        for founded_collection in founded_collections:
            external_id = founded_collection['external_id']
            if founded_collection['external_id'] in existing_collection_external_ids:
                pk = existing_collection_map.get(external_id)
                if pk:
                    old_collection_payload.append({**founded_collection, "pk": pk})
            else:
                new_collection_payload.append({**founded_collection})

        if new_collection_payload:
            MediaCollection.objects.bulk_create(
                [
                    MediaCollection(
                        **coll,
                        media_source=self.media_source
                    ) for coll in new_collection_payload
                ]
            )
        if old_collection_payload:
            MediaCollection.objects.bulk_update(
                [
                    MediaCollection(**coll) for coll in old_collection_payload
                ], fields=[
                    "name"
                ]
            )

    def check_credentials(self) -> bool:
        is_ok = JellyfinService(self.media_source.credentials).check_connexion()
        return is_ok

    @staticmethod
    def validate_credentials(credentials) -> bool:
        is_ok = JellyfinService(credentials).check_connexion()
        return is_ok
