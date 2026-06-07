from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.serializers import DistrictSerializer
from users.services import district_service


class _DistrictPostCountSerializer(drf_serializers.Serializer):
    id = drf_serializers.IntegerField()
    name = drf_serializers.CharField()
    post_count = drf_serializers.IntegerField()


class DistrictPostCountView(APIView):
    """
    GET /users/districts/post-count/  — all districts with their published post count
    """

    permission_classes = [AllowAny]

    def get(self, request):
        districts = district_service.get_districts_post_count()
        return Response(_DistrictPostCountSerializer(districts, many=True).data)


class DistrictListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return [AllowAny()]

    def get(self, request):
        districts = district_service.get_all_districts()
        return Response(DistrictSerializer(districts, many=True).data)

    def post(self, request):
        serializer = DistrictSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            district = district_service.create_district(serializer.validated_data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DistrictSerializer(district).data, status=status.HTTP_201_CREATED)


class DistrictDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def _get_or_404(self, district_id):
        return district_service.get_district_by_id(district_id)

    def get(self, request, district_id):
        district = self._get_or_404(district_id)
        if district is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(DistrictSerializer(district).data)

    def patch(self, request, district_id):
        district = self._get_or_404(district_id)
        if district is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DistrictSerializer(district, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            district = district_service.update_district(district, serializer.validated_data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DistrictSerializer(district).data)

    def delete(self, request, district_id):
        district = self._get_or_404(district_id)
        if district is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        district_service.delete_district(district)
        return Response(status=status.HTTP_204_NO_CONTENT)
