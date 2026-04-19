from rest_framework import serializers


class GenericUserPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        request = self.context.get('request', None)
        if request and hasattr(request, "user"):
            return self.queryset.filter(user=request.user)
        return self.queryset.none()
