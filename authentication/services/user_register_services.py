
import random




Links = [
    "https://talk2cm-assets.s3.ap-south-1.amazonaws.com/profile/default_avatar_image.png",
    "https://talk2cm-assets.s3.ap-south-1.amazonaws.com/profile/green_avatar_logo.png",
    "https://talk2cm-assets.s3.ap-south-1.amazonaws.com/profile/blue_avatar_logo.png",
    "https://talk2cm-assets.s3.ap-south-1.amazonaws.com/profile/indigo_avatar_logo.png",
    "https://talk2cm-assets.s3.ap-south-1.amazonaws.com/profile/yellow_avatar_logo.png",
]


def get_profile_avatar_link():
    return random.choice(Links)