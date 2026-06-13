from django.urls import path

from posts.views.comment_views import CommentDetailView, CommentListCreateView
from posts.views.media_views import MediaUploadUrlView
from posts.views.post_views import FeedView, LatestPostsView, MinisterPostsView, MinistersBulkPostsView, MyPostsView, PostDetailView, PostListCreateView, TrendingPostsView
from posts.views.report_views import AdminPostReportListView, AdminReportedPostListView, AdminReportIssueDetailView, AdminReportIssueListCreateView, PostReportView, ReportIssueListView
from posts.views.vote_views import VoteView
from posts.views.save_view import SavePostView

urlpatterns = [
    path("", PostListCreateView.as_view(), name="post-list-create"),
    path("feed/", FeedView.as_view(), name="post-feed"),
    path("my/", MyPostsView.as_view(), name="my-posts"),
    path("trending/", TrendingPostsView.as_view(), name="post-trending"),
    path("latest/", LatestPostsView.as_view(), name="post-latest"),
    path("media/upload-url/", MediaUploadUrlView.as_view(), name="media-upload-url"),
    path("ministers/", MinistersBulkPostsView.as_view(), name="ministers-bulk-posts"),
    path("minister/<int:minister_id>/", MinisterPostsView.as_view(), name="minister-posts"),
    path("<int:post_id>/", PostDetailView.as_view(), name="post-detail"),
    path("<int:post_id>/comments/", CommentListCreateView.as_view(), name="comment-list-create"),
    path("<int:post_id>/comments/<int:comment_id>/", CommentDetailView.as_view(), name="comment-detail"),
    path("<int:post_id>/vote/", VoteView.as_view(), name="post-vote"),
    path("<int:post_id>/save/", SavePostView.as_view(), name="post-save"),
    path("saved/", SavePostView.as_view(), name="post-saved-list"),
    path("<int:post_id>/report/", PostReportView.as_view(), name="post-report"),
    path("report-issues/", ReportIssueListView.as_view(), name="report-issue-list"),
    path("admin/reports/", AdminPostReportListView.as_view(), name="admin-report-list"),
    path("admin/reported-posts/", AdminReportedPostListView.as_view(), name="admin-reported-post-list"),
    path("admin/report-issues/", AdminReportIssueListCreateView.as_view(), name="admin-report-issue-list-create"),
    path("admin/report-issues/<int:issue_id>/", AdminReportIssueDetailView.as_view(), name="admin-report-issue-detail"),
]
