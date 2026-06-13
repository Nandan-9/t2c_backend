from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError as DRFValidationError

from posts.services import post_service, vote_service
from ..serializers import SavePostSerializer, PostSerializer
from ..models import SavedPost





class SavePostView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_post_or_404(self, post_id):
        post = post_service.get_post_by_id(post_id)
        if not post:
            return None, Response({"detail": "Post not found."}, status=status.HTTP_404_NOT_FOUND)
        return post, None

    def post(self, request, post_id):
        post, err = self._get_post_or_404(post_id)
        if err:
            return err

        serializer = SavePostSerializer(data={"user": request.user.id, "post": post.id})
        if serializer.is_valid():
            serializer.save()
            return Response({"response": "post saved"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, post_id):
        post, err = self._get_post_or_404(post_id)
        if err:
            return err

        deleted, _ = SavedPost.objects.filter(user=request.user, post=post).delete()
        if not deleted:
            return Response({"detail": "Post not saved."}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get(self, request):
        saved_posts = SavedPost.objects.filter(user=request.user).select_related("post")
        posts = [sp.post for sp in saved_posts]
        data = PostSerializer(posts, many=True, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)
    

            

        
