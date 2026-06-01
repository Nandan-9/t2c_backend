from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from posts.models import PostReport, ReportIssue
from posts.serializers import AdminPostReportSerializer, AdminReportedPostSerializer, PostReportSerializer, ReportIssueSerializer
from posts.services import post_service


class ReportIssueListView(APIView):
    """
    GET /posts/report-issues/  — list all available report issue types (authenticated users)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        issues = ReportIssue.objects.all().order_by("name")
        return Response(ReportIssueSerializer(issues, many=True).data)


class AdminReportIssueListCreateView(APIView):
    """
    GET  /posts/admin/report-issues/  — list all issue types
    POST /posts/admin/report-issues/  — create a new issue type
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        issues = ReportIssue.objects.all().order_by("name")
        return Response(ReportIssueSerializer(issues, many=True).data)

    def post(self, request):
        serializer = ReportIssueSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        issue = serializer.save()
        return Response(ReportIssueSerializer(issue).data, status=status.HTTP_201_CREATED)


class AdminReportIssueDetailView(APIView):
    """
    PATCH  /posts/admin/report-issues/<issue_id>/  — update an issue type
    DELETE /posts/admin/report-issues/<issue_id>/  — delete an issue type
    """

    permission_classes = [IsAdminUser]

    def _get_or_404(self, issue_id):
        try:
            return ReportIssue.objects.get(pk=issue_id), None
        except ReportIssue.DoesNotExist:
            return None, Response({"detail": "Issue not found."}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, issue_id):
        issue, err = self._get_or_404(issue_id)
        if err:
            return err
        serializer = ReportIssueSerializer(issue, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, issue_id):
        issue, err = self._get_or_404(issue_id)
        if err:
            return err
        issue.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostReportView(APIView):
    """
    POST /posts/<post_id>/report/  — report a post
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = post_service.get_post_by_id(post_id, viewer=request.user)
        if not post:
            return Response({"detail": "Post not found."}, status=status.HTTP_404_NOT_FOUND)

        if post.author == request.user:
            return Response({"detail": "You cannot report your own post."}, status=status.HTTP_400_BAD_REQUEST)

        if PostReport.objects.filter(post=post, reporter=request.user).exists():
            return Response({"detail": "You have already reported this post."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PostReportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        report = serializer.save(post=post, reporter=request.user)
        return Response(PostReportSerializer(report).data, status=status.HTTP_201_CREATED)


class AdminPostReportListView(APIView):
    """
    GET /posts/admin/reports/           — all reports, newest first
    GET /posts/admin/reports/?issue=2   — filter by issue id
    GET /posts/admin/reports/?post=42   — filter by post id
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = (
            PostReport.objects.select_related("post", "post__author", "reporter", "issue")
            .all()
            .order_by("-created_at")
        )

        issue_id = request.query_params.get("issue")
        if issue_id:
            qs = qs.filter(issue_id=issue_id)

        post_id = request.query_params.get("post")
        if post_id:
            qs = qs.filter(post_id=post_id)

        return Response(AdminPostReportSerializer(qs, many=True).data)


class AdminReportedPostListView(APIView):
    """
    GET /posts/admin/reported-posts/  — each reported post once, with report count + distinct issues
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        from django.db.models import Count, Max

        rows = (
            PostReport.objects.values(
                "post__id",
                "post__heading",
                "post__author__id",
                "post__author__username",
            )
            .annotate(
                report_count=Count("id"),
                last_reported_at=Max("created_at"),
            )
            .order_by("-report_count", "-last_reported_at")
        )

        # attach distinct issues per post in one extra query
        post_ids = [r["post__id"] for r in rows]
        issues_by_post = {}
        for report in (
            PostReport.objects.filter(post_id__in=post_ids)
            .select_related("issue")
            .values("post_id", "issue__id", "issue__name")
            .distinct()
        ):
            issues_by_post.setdefault(report["post_id"], [])
            entry = {"id": report["issue__id"], "name": report["issue__name"]}
            if entry not in issues_by_post[report["post_id"]]:
                issues_by_post[report["post_id"]].append(entry)

        data = []
        for row in rows:
            data.append({
                "post_id": row["post__id"],
                "heading": row["post__heading"],
                "post__author__id": row["post__author__id"],
                "post__author__username": row["post__author__username"],
                "report_count": row["report_count"],
                "last_reported_at": row["last_reported_at"],
                "issues": issues_by_post.get(row["post__id"], []),
            })

        return Response(AdminReportedPostSerializer(data, many=True).data)
