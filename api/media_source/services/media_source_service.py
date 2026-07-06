from media_source.models import MediaSource, MediaCollection
from media_source.services.media_collection_service import MediaCollectionService
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

        collections_to_create = []
        collections_to_update_with_kind = []
        collections_to_update_name_only = []

        for founded_collection in founded_collections:
            external_id = founded_collection["external_id"]
            container_kind = MediaCollectionService.CONTAINER_KIND_MAP.get(
                founded_collection.get("container_kind"),
            )
            pk = existing_collection_map.get(external_id)

            if pk is None:
                collections_to_create.append(
                    MediaCollection(
                        name=founded_collection["name"],
                        external_id=external_id,
                        container_kind=container_kind,
                        media_source=self.media_source,
                    )
                )
            elif container_kind is not None:
                collections_to_update_with_kind.append(
                    MediaCollection(
                        pk=pk,
                        name=founded_collection["name"],
                        container_kind=container_kind,
                    )
                )
            else:
                collections_to_update_name_only.append(
                    MediaCollection(
                        pk=pk,
                        name=founded_collection["name"],
                    )
                )

        if collections_to_create:
            MediaCollection.objects.bulk_create(collections_to_create)
        if collections_to_update_with_kind:
            MediaCollection.objects.bulk_update(
                collections_to_update_with_kind,
                fields=["name", "container_kind"],
            )
        if collections_to_update_name_only:
            MediaCollection.objects.bulk_update(
                collections_to_update_name_only,
                fields=["name"],
            )

    def check_credentials(self) -> bool:
        is_ok = JellyfinService(self.media_source.credentials).check_connexion()
        return is_ok

    @staticmethod
    def validate_credentials(credentials) -> bool:
        is_ok = JellyfinService(credentials).check_connexion()
        return is_ok
