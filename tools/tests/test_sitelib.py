"""sitelib 的單元測試：連結化、refs.md 表格解析、主要問題判定、程式碼路徑轉連結。
執行：.venv/bin/python -m unittest discover -s tools/tests -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sitelib  # noqa: E402


class LinkifyHtml(unittest.TestCase):
    def test_bare_url_before_fullwidth_punctuation(self):
        out = sitelib.linkify_html("來源：https://idohl.org/team ；https://idohl.org/")
        self.assertIn('<a href="https://idohl.org/team">https://idohl.org/team</a> ；', out)
        self.assertIn('<a href="https://idohl.org/">https://idohl.org/</a>', out)

    def test_trailing_ascii_punctuation_stays_outside(self):
        out = sitelib.linkify_html("見 https://doi.org/10.1016/j.poetic.2024.101864. 同儕審查")
        self.assertIn('<a href="https://doi.org/10.1016/j.poetic.2024.101864">https://doi.org/10.1016/j.poetic.2024.101864</a>. 同儕審查', out)

    def test_existing_anchor_code_pre_untouched(self):
        src = ('<p><a href="https://a.b/x">https://a.b/x</a> <code>https://c.d</code></p>'
               '<pre><code>arXiv:2312.17617</code></pre>')
        self.assertEqual(sitelib.linkify_html(src), src)

    def test_arxiv_identifier_with_version(self):
        out = sitelib.linkify_html("預印本 arXiv:2505.23628v3 與 arXiv:2312.17617。")
        self.assertIn('<a href="https://arxiv.org/abs/2505.23628v3">arXiv:2505.23628v3</a>', out)
        self.assertIn('<a href="https://arxiv.org/abs/2312.17617">arXiv:2312.17617</a>。', out)

    def test_doi_plain_and_prefixed(self):
        out = sitelib.linkify_html("DOI:10.1145/3627673.3679791。另見 10.18653/v1/2022.acl-long.307 的數字")
        self.assertIn('DOI:<a href="https://doi.org/10.1145/3627673.3679791">10.1145/3627673.3679791</a>。', out)
        self.assertIn('<a href="https://doi.org/10.18653/v1/2022.acl-long.307">10.18653/v1/2022.acl-long.307</a> 的數字', out)

    def test_acl_anthology_ids(self):
        out = sitelib.linkify_html("2024.lrec-main.35 與 2026.lrec2026-1.114；ACL P07-1131")
        self.assertIn('<a href="https://aclanthology.org/2024.lrec-main.35/">2024.lrec-main.35</a>', out)
        self.assertIn('<a href="https://aclanthology.org/2026.lrec2026-1.114/">2026.lrec2026-1.114</a>', out)
        self.assertIn('ACL <a href="https://aclanthology.org/P07-1131/">P07-1131</a>', out)

    def test_schemeless_whitelisted_hosts(self):
        out = sitelib.linkify_html("aclanthology.org/2024.lrec-main.35；anthropic.com/engineering/building-effective-agents；example.com/x")
        self.assertIn('<a href="https://aclanthology.org/2024.lrec-main.35">aclanthology.org/2024.lrec-main.35</a>；', out)
        self.assertIn('<a href="https://anthropic.com/engineering/building-effective-agents">anthropic.com/engineering/building-effective-agents</a>；', out)
        self.assertIn("；example.com/x", out)
        self.assertNotIn('href="https://example.com', out)

    def test_html_entities_inside_url_are_kept(self):
        src = "https://www.ling.sinica.edu.tw/item/en?act=journal&amp;code=download&amp;article_id=92 。"
        out = sitelib.linkify_html(src)
        self.assertIn('<a href="https://www.ling.sinica.edu.tw/item/en?act=journal&amp;code=download&amp;article_id=92">', out)

    def test_year_like_numbers_are_not_anthology_ids(self):
        out = sitelib.linkify_html("2026-07-30 與 2026.07 與 2024 年")
        self.assertNotIn("<a ", out)

    def test_document_filenames_linked_with_map(self):
        out = sitelib.linkify_html("xu2024_generative-ie-survey.pdf 與 unknown.pdf",
                                   doc_links={"xu2024_generative-ie-survey.pdf": ("../papers/xu2024_generative-ie-survey.pdf", "站內 PDF，CC BY 4.0")})
        self.assertIn('<a href="../papers/xu2024_generative-ie-survey.pdf" class="doc" title="站內 PDF，CC BY 4.0">xu2024_generative-ie-survey.pdf</a>', out)
        self.assertIn(" 與 unknown.pdf", out)


class ParseRefsTables(unittest.TestCase):
    SAMPLE = """# refs 總表
| 檔名（refs/ 內） | 作者 | 年 | 標題（短） | 場域 | 同儕審查 | DOI / arXiv | 問題 |
|---|---|---|---|---|---|---|---|
| xu2024_generative-ie-survey.pdf | Xu et al. | 2024 | Generative IE Survey | *Frontiers of CS* | ✅ | arXiv:2312.17617 | ① |
| mo2025_kggen.pdf | Mo et al. | 2025 | KGGen | NeurIPS 2025 | ✅ | arXiv:2502.09956 | ①⑤ |
| （網頁） | Anthropic | 2025 | Agent Skills | eng. blog | ❌ | /x | ③ |

## 方法學基礎文獻（2026-08-22 新增）

對應問題編號 **⑥ 來歷標記／極性／時間記法的設計依據**。

| 檔名（refs/ 內） | 作者 | 年 | 標題（短） | 場域 | 同儕審查 | 主題 |
|---|---|---|---|---|---|---|
| aikhenvald2007_information-source.pdf | Aikhenvald | 2007 | Information source | *IJL* | ✅ | 來歷（類型學） |
| loc2019_edtf-spec.md | Library of Congress | 2019 | EDTF | LOC | 官方標準 | 時間 |
"""

    def test_rows_and_sections(self):
        rows = sitelib.parse_refs_tables(self.SAMPLE)
        self.assertEqual(set(rows), {"xu2024_generative-ie-survey.pdf", "mo2025_kggen.pdf",
                                     "aikhenvald2007_information-source.pdf", "loc2019_edtf-spec.md"})
        self.assertEqual(rows["mo2025_kggen.pdf"]["questions"], "①⑤")
        self.assertEqual(rows["mo2025_kggen.pdf"]["section"], "")
        self.assertEqual(rows["mo2025_kggen.pdf"]["author"], "Mo et al.")
        self.assertEqual(rows["mo2025_kggen.pdf"]["venue"], "NeurIPS 2025")

    def test_section_default_question_when_column_missing(self):
        rows = sitelib.parse_refs_tables(self.SAMPLE)
        self.assertEqual(rows["aikhenvald2007_information-source.pdf"]["questions"], "⑥")
        self.assertEqual(rows["aikhenvald2007_information-source.pdf"]["topic"], "來歷（類型學）")
        self.assertTrue(rows["aikhenvald2007_information-source.pdf"]["section"].startswith("方法學基礎文獻"))


class PrimaryQuestion(unittest.TestCase):
    def test_first_symbol_wins(self):
        self.assertEqual(sitelib.primary_question("④⑥⑤"), "④")

    def test_override_and_default(self):
        self.assertEqual(sitelib.primary_question("", default="⑥"), "⑥")
        self.assertEqual(sitelib.primary_question("⑥", override="④"), "④")
        self.assertIsNone(sitelib.primary_question(""))


class CodePathsToLinks(unittest.TestCase):
    def test_code_span_paths_become_links(self):
        resolver = {"notes/_對照矩陣.md": "matrix.html", "refs/mbakwe2009_review.pdf": "../papers/mbakwe2009_review.pdf"}.get
        md = "見 `notes/_對照矩陣.md` 與 `refs/mbakwe2009_review.pdf`，以及 `life_nodes.py`。"
        out = sitelib.code_paths_to_links(md, resolver)
        self.assertIn("[`notes/_對照矩陣.md`](matrix.html)", out)
        self.assertIn("[`refs/mbakwe2009_review.pdf`](../papers/mbakwe2009_review.pdf)", out)
        self.assertIn("`life_nodes.py`", out)
        self.assertNotIn("[`life_nodes.py`]", out)

    def test_already_linked_code_untouched(self):
        md = "[`notes/_對照矩陣.md`](matrix.html)"
        self.assertEqual(sitelib.code_paths_to_links(md, {"notes/_對照矩陣.md": "x.html"}.get), md)


if __name__ == "__main__":
    unittest.main()
