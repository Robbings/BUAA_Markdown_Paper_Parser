import re
from typing import Dict, List, Tuple, Any
from .base import ParsingStrategy


class ThesisParsingStrategy(ParsingStrategy):
    """
    Parsing strategy for Chinese doctoral thesis format.

    Typical structure:
    - # 博士学位论文
    - # [论文标题]
    - # 摘要 / Abstract
    - # 目录
    - # 第一章 / 第二章 ... (chapters)
    - ## 1.1 / 1.2 ... (sections)
    - ### 1.1.1 / 1.1.2 ... (clauses)
    - # 参考文献
    - # 作者介绍
    """

    def _define_keywords_config(self) -> List[Dict[str, Any]]:
        """Define keyword patterns for Chinese doctoral thesis."""
        return [
            {
                # 章 (Chapter)
                "keyword": r"第.*章",
                "description": "chapter",
                "level": 1,
            },
            {
                # 节 (Section) - e.g., 1.1, 2.3
                "keyword": r"\b\d+\.\d+\b",
                "description": "section",
                "level": 2,
            },
            {
                # 条 (Clause) - e.g., 1.1.1, 2.3.4
                "keyword": r"\b\d+\.\d+\.\d+\b",
                "description": "clause",
                "level": 3,
            },
            {
                # 款 (Item) - e.g., (1), (2)
                "keyword": r"（\d+）",
                "description": "item",
                "level": 4,
            },
            {
                # 中文摘要
                "keyword": r"摘\s*要",
                "description": "abstract_ch",
                "level": 1,
            },
            {
                # English Abstract
                "keyword": r"Abstract",
                "description": "abstract_en",
                "level": 1,
            },
            {
                # 作者介绍
                "keyword": r"作者介绍",
                "description": "author_introduction",
                "level": -1,
            },
            {
                # 目录
                "keyword": r"目\s*录",
                "description": "table_of_contents",
                "level": 1,
            },
            {
                # 参考文献
                "keyword": r"参\s*考\s*文\s*献",
                "description": "references",
                "level": 1,
            },
            {
                # 图清单
                "keyword": r"图\s*清\s*单",
                "description": "list_of_figures",
                "level": 1,
            },
            {
                # 表清单
                "keyword": r"表\s*清\s*单",
                "description": "list_of_tables",
                "level": 1,
            },
            {
                # 取得的研究成果
                "keyword": r"取得的研究成果",
                "description": "research_results",
                "level": -1,
            }
        ]

    def get_detection_features(self) -> Dict[str, Any]:
        """
        Define features for detecting Chinese doctoral thesis format.

        Key characteristics:
        - Must have "博士学位论文" header
        - Chinese chapter markers: 第一章, 第二章, etc.
        - Chinese abstract: 摘要
        - Numbered sections: 1.1, 1.2, etc.
        - Chinese references: 参考文献
        """
        return {
            'required_patterns': [
                # Must have doctoral thesis marker
                (r"博\s*士\s*学\s*位\s*论\s*文", 10.0),
            ],
            'optional_patterns': [
                # Chinese chapter markers
                (r"第[一二三四五六七八九十]+章", 5.0),
                (r"第\d+章", 5.0),
                # Chinese abstract
                (r"摘\s*要", 3.0),
                # Chinese references
                (r"参\s*考\s*文\s*献", 3.0),
                # Numbered sections
                (r"#\s*\d+\.\d+", 2.0),
                # Table of contents
                (r"目\s*录", 2.0),
                # Author introduction
                (r"作者介绍", 1.0),
                # Research results
                (r"取得的研究成果", 1.0),
            ],
            'structural_hints': [
                (self._check_chinese_chapter_structure, 3.0),
                (self._check_hierarchical_numbering, 2.0),
            ],
            'exclusion_patterns': [
                # If it has IEEE patterns, it's not a thesis
                r"IEEE.*Member",
                r"Index Terms—",
                # If it has conference patterns (AAAI, etc.)
                r"Association for the Advancement of Artificial Intelligence",
            ]
        }

    def _check_chinese_chapter_structure(self, content: str, lines: List[str]) -> float:
        """
        Check if the document has Chinese chapter structure.

        Returns:
            Score between 0.0 and 1.0
        """
        chapter_pattern = r"#\s*第[一二三四五六七八九十\d]+章"
        chapters = re.findall(chapter_pattern, content)

        if len(chapters) >= 3:
            return 1.0
        elif len(chapters) >= 1:
            return 0.5
        return 0.0

    def _check_hierarchical_numbering(self, content: str, lines: List[str]) -> float:
        """
        Check if the document uses hierarchical numbering (1.1, 1.1.1, etc.).

        Returns:
            Score between 0.0 and 1.0
        """
        # Look for patterns like ## 1.1, ### 1.1.1
        section_pattern = r"##\s*\d+\.\d+\s"
        clause_pattern = r"###\s*\d+\.\d+\.\d+\s"

        sections = re.findall(section_pattern, content)
        clauses = re.findall(clause_pattern, content)

        total_numbered = len(sections) + len(clauses)

        if total_numbered >= 10:
            return 1.0
        elif total_numbered >= 5:
            return 0.7
        elif total_numbered >= 2:
            return 0.4
        return 0.0

    def parse(self, lines: List[str]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Parse Chinese doctoral thesis using a specialized state machine.

        This implements the original parsing logic from markdown_parser.py,
        which includes:
        - Stage 0: Wait for "博士学位论文" header
        - Stage 1: Capture thesis title
        - Stage 2: Capture metadata before first heading
        - Stage 3: Parse main content structure
        - Stage 4: Capture trailing metadata

        Args:
            lines: List of non-empty lines

        Returns:
            Tuple of (metadata, parse_tree)
        """
        stage = 0
        metadata = {}
        tree = []
        node_stack = []
        last_part = False
        last_description = None

        def add_node(level, description, title, line_num):
            node = {
                "level": level,
                "description": description,
                "title": title.strip("# ").strip(),
                "line": line_num,
                "content": "",
                "children": []
            }

            while node_stack and node_stack[-1]["level"] >= level:
                node_stack.pop()

            if node_stack and level > 0:
                node_stack[-1]["children"].append(node)
            else:
                tree.append(node)
            node_stack.append(node)

        def add_content(line):
            if node_stack:
                node_stack[-1]["content"] += line.strip() + "\n"

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Stage 0: Wait for "博士学位论文" header
            if stage == 0:
                if line.startswith("#") and re.search(r"博\s*士\s*学\s*位\s*论\s*文", line, re.IGNORECASE):
                    stage = 1

            # Stage 1: Capture thesis title
            elif stage == 1:
                metadata["title"] = line.strip("# ").strip()
                metadata["raw"] = "# title: " + metadata["title"] + "\n\n"
                stage = 2

            # Stage 2: Capture metadata before first heading
            elif stage == 2:
                if line.startswith("#"):
                    stage = 3
                    metadata["raw"] += "\n"
                    continue
                metadata["raw"] += line + "\n"
                i += 1
                continue

            # Stage 3: Parse main content structure
            elif stage == 3:
                if line.startswith("#"):
                    if last_part:
                        stage = 4
                        continue
                    level, description = self._match_keyword_level(line)
                    if description == "references":
                        last_part = True
                    if level is not None:
                        add_node(level, description, line, i)
                    else:
                        add_content(line)
                else:
                    if not re.search(r"^\s*参\s*考\s*文\s*献\s*$", line):
                        add_content(line)
                    else:
                        last_part = True
                        add_node(1, "references", line, i)

            # Stage 4: Capture trailing metadata
            elif stage == 4:
                if line.startswith("#"):
                    level, last_description = self._match_keyword_level(line)
                    if level is None:
                        last_description = "raw"
                    if last_description not in metadata:
                        metadata[last_description] = ""
                    metadata[last_description] += "\n" + line.strip() + "\n"
                else:
                    if last_description not in metadata:
                        metadata[last_description] = ""
                    metadata[last_description] += line.strip() + "\n"

            i += 1

        return metadata, tree
