import pytest

from pipeline.ids import article_id, law_id


@pytest.mark.parametrize("name,slug", [
    ("Зөвшөөрлийн тухай хууль", "zovshoorliin-tukhai-khuuli"),
    ("Тусгай зөвшөөрлийн тухай хууль", "tusgai-zovshoorliin-tukhai-khuuli"),
    ("Зөрчлийн тухай хууль", "zorchliin-tukhai-khuuli"),
    ("  Ашигт малтмалын тухай хууль ", "ashigt-maltmalyn-tukhai-khuuli"),
    ("Монгол Улсын Үндсэн хууль", "mongol-ulsyn-undsen-khuuli"),
])
def test_law_id(name, slug):
    assert law_id(name) == slug


def test_article_id():
    assert article_id("zorchliin-tukhai-khuuli", "11.4") == "zorchliin-tukhai-khuuli:11.4"
