from media_source.models import MediaContainer
from rule_engine.services.category_normalizer.category_normalizer_with_llm import CategoryNormalizerWithLlm
from rule_engine.services.category_normalizer.category_normalizer_without_llm import CategoryNormalizerWithoutLlm


class MediaContainerService:
    """
    Set but doesnt save
    On purpose.
    """

    def __init__(self, media_container: MediaContainer):
        self.media_container = media_container

    def normalize_data(self, use_llm=False) -> MediaContainer:
        self._set_media_container_category(use_llm)
        return self.media_container

    def _set_media_container_category(self, use_llm):
        if use_llm:
            service = CategoryNormalizerWithLlm(media_container_raw_data=self.media_container.raw_data)
            categories = service.get_categories()
        else:
            service = CategoryNormalizerWithoutLlm(media_container_raw_data=self.media_container.raw_data)
            categories = service.get_categories()
        print(categories)
        self.media_container.categories = categories
