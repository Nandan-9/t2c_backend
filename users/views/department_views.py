from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.serializers import DepartmentSerializer
from users.services import department_service


class _TopDepartmentSerializer(drf_serializers.Serializer):
    id = drf_serializers.IntegerField()
    name = drf_serializers.CharField()
    post_count = drf_serializers.IntegerField()


class TopDepartmentsView(APIView):
    """
    GET /users/departments/top/  — departments ranked by published post count (min 6 returned)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        departments = department_service.get_top_departments()
        data = _TopDepartmentSerializer(departments, many=True).data
        return Response(data)


class DepartmentListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get(self, request):
        departments = department_service.get_all_departments()
        serializer = DepartmentSerializer(departments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = DepartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            department = department_service.create_department(serializer.validated_data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DepartmentSerializer(department).data, status=status.HTTP_201_CREATED)


class DepartmentDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def _get_department_or_404(self, department_id):
        dept = department_service.get_department_by_id(department_id)
        if dept is None:
            return None
        return dept

    def get(self, request, department_id):
        dept = self._get_department_or_404(department_id)
        if dept is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(DepartmentSerializer(dept).data)

    def patch(self, request, department_id):
        dept = self._get_department_or_404(department_id)
        if dept is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DepartmentSerializer(dept, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            dept = department_service.update_department(dept, serializer.validated_data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DepartmentSerializer(dept).data)

    def delete(self, request, department_id):
        dept = self._get_department_or_404(department_id)
        if dept is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        department_service.delete_department(dept)
        return Response(status=status.HTTP_204_NO_CONTENT)
