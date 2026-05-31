from django.urls import path

from posts.views.comment_views import CommentDetailView, CommentListCreateView
from posts.views.media_views import MediaUploadUrlView
from posts.views.post_views import FeedView, MinisterPostsView, PostDetailView, PostListCreateView, TrendingPostsView
from posts.views.vote_views import VoteView

urlpatterns = [
    path("", PostListCreateView.as_view(), name="post-list-create"),
    path("feed/", FeedView.as_view(), name="post-feed"),
    path("trending/", TrendingPostsView.as_view(), name="post-trending"),
    path("media/upload-url/", MediaUploadUrlView.as_view(), name="media-upload-url"),
    path("minister/<int:minister_id>/", MinisterPostsView.as_view(), name="minister-posts"),
    path("<int:post_id>/", PostDetailView.as_view(), name="post-detail"),
    path("<int:post_id>/comments/", CommentListCreateView.as_view(), name="comment-list-create"),
    path("<int:post_id>/comments/<int:comment_id>/", CommentDetailView.as_view(), name="comment-detail"),
    path("<int:post_id>/vote/", VoteView.as_view(), name="post-vote"),
]
