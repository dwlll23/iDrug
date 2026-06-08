from rest_framework import serializers
from web.ms import User


class UserModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "password"]