import re
from typing import Dict, List, Tuple, Any
from .base import ParsingStrategy


class JournalPaperStrategy(ParsingStrategy):
    """
    Parsing strategy for IEEE-style journal papers.

    Typical structure:
    - # [Paper Title]
    - Authors and affiliations
    - # Abstract (sometimes as paragraph with "Abstract—")
    - Index Terms—
    - # I. INTRODUCTION
    - # II. RELATED WORK / BACKGROUND
    - # III. METHOD / PROPOSED APPROACH
    - # IV. EXPERIMENTS / RESULTS
    - ## A. Subsection
    - ## B. Subsection
    - # V. CONCLUSION
    - # REFERENCES / References
    """

    def _define_keywords_config(self) -> List[Dict[str, Any]]:
        """Define keyword patterns for IEEE journal papers."""
        return [
            {
                # Introduction specifically (should come first for priority)
                "keyword": r"I\.\s+INTRODUCTION",
                "description": "introduction",
                "level": 1,
            },
            {
                # Related Work / Background
                "keyword": r"(II|III)\.\s+(RELATED WORK|BACKGROUND)",
                "description": "related_work",
                "level": 1,
            },
            {
                # Method/Methodology
                "keyword": r"(III|IV|V)\.\s+(METHOD|METHODOLOGY|PROPOSED)",
                "description": "methodology",
                "level": 1,
            },
            {
                # Results/Experiments
                "keyword": r"(IV|V|VI)\.\s+(RESULT|EXPERIMENT)",
                "description": "results",
                "level": 1,
            },
            {
                # Discussion
                "keyword": r"(V|VI|VII)\.\s+DISCUSSION",
                "description": "discussion",
                "level": 1,
            },
            {
                # Conclusion
                "keyword": r"(VI|VII|VIII|IX|X)\.\s+CONCLUSION",
                "description": "conclusion",
                "level": 1,
            },
            {
                # Abstract (can be heading or paragraph marker)
                "keyword": r"Abstract",
                "description": "abstract",
                "level": 1,
            },
            {
                # Index Terms
                "keyword": r"Index Terms[—\-]",
                "description": "index_terms",
                "level": -1,
            },
            {
                # Subsections with letters (A., B., C., etc.)
                "keyword": r"[A-Z]\.\s+[A-Z]",
                "description": "subsection",
                "level": 2,
            },
            {
                # References
                "keyword": r"(REFERENCES|References)",
                "description": "references",
                "level": 1,
            },
            {
                # Acknowledgment
                "keyword": r"(ACKNOWLEDGMENT|ACKNOWLEDGEMENT)",
                "description": "acknowledgment",
                "level": 1,
            },
            {
                # Main sections with Roman numerals (generic fallback, should be last)
                "keyword": r"[IVX]+\.\s+[A-Z]",
                "description": "section",
                "level": 1,
            },
        ]

    def get_detection_features(self) -> Dict[str, Any]:
        """
        Define features for detecting IEEE journal paper format.

        Key characteristics:
        - Roman numeral section numbering (I., II., III., etc.)
        - Letter subsection numbering (A., B., C., etc.)
        - "Index Terms—" marker
        - IEEE/ACM/other society markers
        - All-caps section titles
        """
        return {
            'required_patterns': [
                # Must have Roman numeral sections
                (r"#\s+[IVX]+\.\s+[A-Z]{3,}", 10.0),
            ],
            'optional_patterns': [
                # Index Terms marker
                (r"Index Terms[—\-]", 5.0),
                # IEEE/ACM markers
                (r"(IEEE|ACM).*?(Member|Fellow|Transactions)", 4.0),
                # Common journal paper sections with Roman numerals
                (r"#\s+I\.\s+INTRODUCTION", 4.0),
                (r"#\s+II\.\s+(RELATED WORK|BACKGROUND)", 3.0),
                (r"#\s+[IVX]+\.\s+CONCLUSION", 3.0),
                # Letter-numbered subsections
                (r"##\s+[A-Z]\.\s+[A-Z]", 3.0),
                # Abstract marker
                (r"^# Abstract$", 2.0),
                (r"Abstract[—\-]", 2.0),
                # References
                (r"^# (REFERENCES|References)$", 2.0),
                # DOI marker
                (r"Digital Object Identifier", 1.0),
                (r"doi\.org", 1.0),
            ],
            'structural_hints': [
                (self._check_roman_numeral_structure, 4.0),
                (self._check_letter_subsections, 2.0),
                (self._check_uppercase_sections, 2.0),
            ],
            'exclusion_patterns': [
                # If it has Chinese thesis markers, it's not a journal paper
                r"博士学位论文",
                r"第.*章",
                # If it has AAAI conference marker
                r"Association for the Advancement of Artificial Intelligence",
            ]
        }

    def _check_roman_numeral_structure(self, content: str, lines: List[str]) -> float:
        """
        Check if the document uses Roman numeral section numbering.

        Returns:
            Score between 0.0 and 1.0
        """
        # Look for Roman numeral patterns in headings
        pattern = r"^#\s+[IVX]+\.\s+[A-Z]"
        matches = re.findall(pattern, content, re.MULTILINE)

        # Check for sequential Roman numerals
        roman_numerals = []
        for match in matches:
            numeral = re.search(r"[IVX]+", match).group()
            roman_numerals.append(numeral)

        # Score based on quantity and variety
        if len(matches) >= 5:
            return 1.0
        elif len(matches) >= 3:
            return 0.8
        elif len(matches) >= 1:
            return 0.5
        return 0.0

    def _check_letter_subsections(self, content: str, lines: List[str]) -> float:
        """
        Check if the document uses letter-based subsection numbering.

        Returns:
            Score between 0.0 and 1.0
        """
        # Look for letter subsections (A., B., C., etc.)
        pattern = r"^##\s+[A-Z]\.\s+[A-Z]"
        matches = re.findall(pattern, content, re.MULTILINE)

        if len(matches) >= 3:
            return 1.0
        elif len(matches) >= 1:
            return 0.6
        return 0.0

    def _check_uppercase_sections(self, content: str, lines: List[str]) -> float:
        """
        Check if section titles are in uppercase (common in IEEE papers).

        Returns:
            Score between 0.0 and 1.0
        """
        # Find all first-level headings
        headings = re.findall(r"^#\s+(.+)$", content, re.MULTILINE)

        if not headings:
            return 0.0

        # Count uppercase headings (excluding title)
        uppercase_count = 0
        for heading in headings[1:]:  # Skip title
            # Remove Roman numerals and check if rest is uppercase
            cleaned = re.sub(r"^[IVX]+\.\s+", "", heading)
            # Check if at least 80% of letters are uppercase
            letters = [c for c in cleaned if c.isalpha()]
            if letters:
                uppercase_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
                if uppercase_ratio > 0.8:
                    uppercase_count += 1

        if len(headings) > 1:
            ratio = uppercase_count / (len(headings) - 1)
            return ratio
        return 0.0

    def parse(self, lines: List[str]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Parse IEEE journal paper.

        Extracts:
        - Title (first heading)
        - Authors and affiliations (before Abstract)
        - Abstract
        - Index Terms
        - Main sections (Roman numerals)
        - Subsections (letters)

        Args:
            lines: List of non-empty lines

        Returns:
            Tuple of (metadata, parse_tree)
        """
        metadata = {}
        tree = []
        node_stack = []

        stage = 0  # 0: before title, 1: title found, 2: before abstract, 3: main content
        current_section = None

        def add_node(level, description, title, line_num):
            node = {
                "level": level,
                "description": description,
                "title": title.strip("# ").strip(),
                "line": line_num,
                "content": "",
                "children": []
            }

            # Pop nodes from stack until we find the parent
            while node_stack and node_stack[-1]["level"] >= level:
                node_stack.pop()

            # Attach to parent or root
            if node_stack and level > 0:
                node_stack[-1]["children"].append(node)
            else:
                tree.append(node)

            node_stack.append(node)
            return node

        def add_content(line):
            if node_stack:
                node_stack[-1]["content"] += line.strip() + "\n"
            elif stage == 2 and "authors" in metadata:
                # Before abstract, accumulate author info
                metadata["authors"] += line.strip() + "\n"

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Stage 0: Look for title (first heading)
            if stage == 0:
                if line.startswith("# "):
                    metadata["title"] = line.strip("# ").strip()
                    metadata["authors"] = ""
                    stage = 1

            # Stage 1: After title, before abstract
            elif stage == 1:
                # Check if this is the abstract
                if line.startswith("# Abstract") or re.match(r"^# [IVX]+\.", line):
                    stage = 2
                    continue
                else:
                    # Accumulate author/affiliation info
                    metadata["authors"] += line + "\n"

            # Stage 2+: Main content
            if stage >= 1 and line.startswith("#"):
                level, description = self._match_keyword_level(line)

                if description == "abstract":
                    stage = 3
                    add_node(1, "abstract", line, i)
                elif level is not None:
                    stage = 3
                    add_node(level, description, line, i)
                else:
                    # Unrecognized heading, try to infer level
                    heading_level = len(line) - len(line.lstrip('#'))
                    if heading_level == 1:
                        add_node(1, "section", line, i)
                    elif heading_level == 2:
                        add_node(2, "subsection", line, i)
                    else:
                        add_content(line)
            elif stage >= 2:
                # Check for Index Terms
                if "Index Terms" in line and "index_terms" not in metadata:
                    metadata["index_terms"] = line
                else:
                    add_content(line)

            i += 1

        return metadata, tree
