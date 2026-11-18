import auth
import post


def test_modulos_importam_sem_rede():
    assert callable(post.main)
    assert callable(auth.main)
