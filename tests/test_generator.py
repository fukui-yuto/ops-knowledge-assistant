"""generator モジュールのテスト（LLM呼び出しはモック）。"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.generator import TEMPLATE_KEYWORDS, ProcedureGenerator


def test_template_keywords_structure():
    """テンプレートキーワードマッピングが正しい構造であること。"""
    assert isinstance(TEMPLATE_KEYWORDS, dict)
    for name, keywords in TEMPLATE_KEYWORDS.items():
        assert isinstance(name, str)
        assert isinstance(keywords, list)
        assert all(isinstance(k, str) for k in keywords)


def test_auto_select_template_k8s(tmp_path):
    """K8s関連タイトルでk8sテンプレートが選定されること。"""
    # テンプレートを作成
    (tmp_path / "default.md").write_text("default template")
    (tmp_path / "k8s.md").write_text("k8s template")

    with patch("src.generator.config") as mock_config:
        mock_config.google_api_key = "test"
        mock_config.generation_model = "test"
        mock_config.templates_path = str(tmp_path)
        with patch("src.generator.genai"):
            with patch("src.generator.Retriever"):
                gen = ProcedureGenerator(templates_dir=tmp_path)

    result = gen.auto_select_template("K8s Pod再起動手順")
    assert result == "k8s"


def test_auto_select_template_default(tmp_path):
    """該当なしの場合defaultが選定されること。"""
    (tmp_path / "default.md").write_text("default template")

    with patch("src.generator.config") as mock_config:
        mock_config.google_api_key = "test"
        mock_config.generation_model = "test"
        mock_config.templates_path = str(tmp_path)
        with patch("src.generator.genai"):
            with patch("src.generator.Retriever"):
                gen = ProcedureGenerator(templates_dir=tmp_path)

    result = gen.auto_select_template("何か不明な手順")
    assert result == "default"


def test_auto_select_template_network(tmp_path):
    """ネットワーク関連タイトルでnetworkが選定されること。"""
    (tmp_path / "default.md").write_text("default template")
    (tmp_path / "network.md").write_text("network template")

    with patch("src.generator.config") as mock_config:
        mock_config.google_api_key = "test"
        mock_config.generation_model = "test"
        mock_config.templates_path = str(tmp_path)
        with patch("src.generator.genai"):
            with patch("src.generator.Retriever"):
                gen = ProcedureGenerator(templates_dir=tmp_path)

    result = gen.auto_select_template("ネットワーク設定変更手順")
    assert result == "network"


def test_list_templates(tmp_path):
    """テンプレート一覧が正しく返ること。"""
    (tmp_path / "default.md").write_text("template")
    (tmp_path / "k8s.md").write_text("template")
    (tmp_path / "not_md.txt").write_text("ignored")

    with patch("src.generator.config") as mock_config:
        mock_config.google_api_key = "test"
        mock_config.generation_model = "test"
        mock_config.templates_path = str(tmp_path)
        with patch("src.generator.genai"):
            with patch("src.generator.Retriever"):
                gen = ProcedureGenerator(templates_dir=tmp_path)

    templates = gen.list_templates()
    assert "default" in templates
    assert "k8s" in templates
    assert "not_md" not in templates


def test_load_template(tmp_path):
    """テンプレートの読み込みが正しく行われること。"""
    (tmp_path / "default.md").write_text("# {{title}}\n\ntemplate content", encoding="utf-8")

    with patch("src.generator.config") as mock_config:
        mock_config.google_api_key = "test"
        mock_config.generation_model = "test"
        mock_config.templates_path = str(tmp_path)
        with patch("src.generator.genai"):
            with patch("src.generator.Retriever"):
                gen = ProcedureGenerator(templates_dir=tmp_path)

    content = gen.load_template("default")
    assert "{{title}}" in content


def test_load_template_not_found(tmp_path):
    """存在しないテンプレートでFileNotFoundErrorが発生すること。"""
    with patch("src.generator.config") as mock_config:
        mock_config.google_api_key = "test"
        mock_config.generation_model = "test"
        mock_config.templates_path = str(tmp_path)
        with patch("src.generator.genai"):
            with patch("src.generator.Retriever"):
                gen = ProcedureGenerator(templates_dir=tmp_path)

    with pytest.raises(FileNotFoundError):
        gen.load_template("nonexistent")
