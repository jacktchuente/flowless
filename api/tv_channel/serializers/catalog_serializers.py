from rest_framework import serializers

from tv_channel.models import Catalog


class CatalogCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Catalog
        fields = ("id", "name", "description")

    def to_representation(self, instance):
        return CatalogSerializer().to_representation(instance)


class CatalogUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Catalog
        fields = ("id", "name", "description")

    def to_representation(self, instance):
        return CatalogSerializer().to_representation(instance)


class CatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Catalog
        fields = ("id", "name", "description")
