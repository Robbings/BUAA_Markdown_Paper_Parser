import re
from typing import Dict, List, Tuple, Any
from .base import ParsingStrategy


class ConferencePaperStrategy(ParsingStrategy):
    """
    Parsing strategy for conference papers (AAAI, NeurIPS, ICML, etc.).

    Typical structure:
    - # [Paper Title]
    - Authors and affiliations
    - # Abstract
    - # Introduction
    - # Related Work / Background
    - # Method / Methodology
    - ## Subsections (optional)
    - # Results / Experiments
    - # Discussion
    - # Conclusion
    - # References
    """

    def _define_keywords_config(self) -> List[Dict[str, Any]]:
        """Define keyword patterns for conference papers."""
        return [
            {
                # Abstract
                "keyword": r"Abstract",
                "description": "abstract",
                "level": 1,
            },
            {
                # Introduction
                "keyword": r"Introduction",
                "description": "introduction",
                "level": 1,
            },
            {
                # Related Work / Background
                "keyword": r"(Related Work|Background|Literature Review)",
                "description": "related_work",
                "level": 1,
            },
            {
                # Method/Methodology/Approach
                "keyword": r"(Method|Methodology|Approach|Proposed Method|Our Approach)",
                "description": "methodology",
                "level": 1,
            },
            {
                # Results/Experiments
                "keyword": r"(Results|Experiments|Experimental Results|Evaluation)",
                "description": "results",
                "level": 1,
            },
            {
                # Discussion
                "keyword": r"Discussion",
                "description": "discussion",
                "level": 1,
            },
            {
                # Conclusion
                "keyword": r"(Conclusion|Conclusions|Concluding Remarks)",
                "description": "conclusion",
                "level": 1,
            },
            {
                # References
                "keyword": r"References",
                "description": "references",
                "level": 1,
            },
            {
                # Acknowledgments
                "keyword": r"(Acknowledgment|Acknowledgments|Acknowledgement|Acknowledgements)",
                "description": "acknowledgment",
                "level": 1,
            },
            {
                # Appendix
                "keyword": r"(Appendix|Appendices)",
                "description": "appendix",
                "level": 1,
            },
        ]

    def get_detection_features(self) -> Dict[str, Any]:
        """
        Define features for detecting conference paper format.

        Key characteristics:
        - No Roman numerals in section numbering
        - Title case section headings (not all caps)
        - Standard sections: Abstract, Introduction, Conclusion, References
        - Often has conference markers (AAAI, NeurIPS, etc.)
        - Copyright notices from conferences
        """
        return {
            'required_patterns': [
                # Must have at least one of these standard sections
                (r"^# (Abstract|Introduction)$", 8.0),
            ],
            'optional_patterns': [
                # Conference markers
                (r"(AAAI|NeurIPS|ICML|ICLR|ACL|EMNLP|CVPR|ICCV|ECCV)", 4.0),
                (r"Association for the Advancement of Artificial Intelligence", 4.0),
                (r"Conference on", 3.0),
                # Standard conference paper sections
                (r"^# Abstract$", 4.0),
                (r"^# Introduction$", 4.0),
                (r"^# Related Work$", 3.0),
                (r"^# (Method|Methodology)$", 3.0),
                (r"^# (Results|Experiments)$", 3.0),
                (r"^# Discussion$", 2.0),
                (r"^# (Conclusion|Conclusions)$", 4.0),
                (r"^# References$", 3.0),
                # Copyright notices
                (r"Copyright ©.*20\d{2}", 2.0),
                (r"All rights reserved", 1.0),
                # Extended version links (common in conferences)
                (r"Extended version", 1.0),
                (r"arXiv", 1.0),
            ],
            'structural_hints': [
                (self._check_standard_section_flow, 5.0),
                (self._check_title_case_sections, 3.0),
                (self._check_no_roman_numerals, 2.0),
            ],
            'exclusion_patterns': [
                # If it has Chinese thesis markers
                r"博士学位论文",
                r"第.*章",
                # If it has IEEE journal markers
                r"IEEE.*?(Member|Fellow)",
                r"Index Terms[—\-]",
                # If sections use Roman numerals
                r"^# [IVX]+\.\s+[A-Z]",
            ]
        }

    def _check_standard_section_flow(self, content: str, lines: List[str]) -> float:
        """
        Check if the document follows standard conference paper section flow.

        Typical flow: Abstract → Introduction → Method → Results → Conclusion → References

        Returns:
            Score between 0.0 and 1.0
        """
        # Define expected section sequence
        expected_sections = [
            r"^# Abstract$",
            r"^# Introduction$",
            r"^# (Related Work|Background)",
            r"^# (Method|Methodology|Approach)",
            r"^# (Results|Experiments|Evaluation)",
            r"^# (Discussion|Analysis)",
            r"^# (Conclusion|Conclusions)",
            r"^# References$",
        ]

        found_sections = []
        for pattern in expected_sections:
            if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                found_sections.append(pattern)

        # Score based on how many expected sections are found
        score = len(found_sections) / len(expected_sections)

        # Bonus if they appear in reasonable order
        section_positions = []
        for pattern in expected_sections:
            match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
            if match:
                section_positions.append(match.start())

        # Check if positions are monotonically increasing (rough order check)
        if len(section_positions) >= 3:
            is_ordered = all(section_positions[i] < section_positions[i+1]
                           for i in range(len(section_positions)-1))
            if is_ordered:
                score = min(1.0, score + 0.2)  # Bonus for correct order

        return score

    def _check_title_case_sections(self, content: str, lines: List[str]) -> float:
        """
        Check if section titles use title case (not all caps).

        Conference papers typically use title case, not uppercase like journals.

        Returns:
            Score between 0.0 and 1.0
        """
        # Find all first-level headings
        headings = re.findall(r"^# (.+)$", content, re.MULTILINE)

        if len(headings) < 2:
            return 0.0

        # Count title case headings (excluding the paper title)
        title_case_count = 0
        for heading in headings[1:]:  # Skip paper title
            # Title case: first letter uppercase, has lowercase letters
            has_uppercase = any(c.isupper() for c in heading)
            has_lowercase = any(c.islower() for c in heading)
            not_all_caps = not heading.isupper()

            if has_uppercase and has_lowercase and not_all_caps:
                title_case_count += 1

        ratio = title_case_count / (len(headings) - 1)
        return ratio

    def _check_no_roman_numerals(self, content: str, lines: List[str]) -> float:
        """
        Check that sections don't use Roman numeral numbering.

        Returns:
            Score between 0.0 and 1.0 (1.0 = no Roman numerals found)
        """
        # Look for Roman numeral patterns
        pattern = r"^# [IVX]+\.\s+"
        matches = re.findall(pattern, content, re.MULTILINE)

        # Fewer matches = higher score
        if len(matches) == 0:
            return 1.0
        elif len(matches) == 1:
            return 0.3  # Might be coincidence
        else:
            return 0.0  # Definitely uses Roman numerals

    def parse(self, lines: List[str]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Parse conference paper.

        Extracts:
        - Title (first heading)
        - Authors and affiliations (before Abstract)
        - Abstract and main sections
        - Subsections

        Args:
            lines: List of non-empty lines

        Returns:
            Tuple of (metadata, parse_tree)
        """
        metadata = {}
        tree = []
        node_stack = []

        stage = 0  # 0: before title, 1: title found, 2: before abstract, 3: main content

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
                # Check if this is the abstract or first section
                if line.startswith("# "):
                    stage = 2
                    continue
                else:
                    # Accumulate author/affiliation info
                    metadata["authors"] += line + "\n"

            # Stage 2+: Main content
            if stage >= 1 and line.startswith("#"):
                level, description = self._match_keyword_level(line)

                if level is not None:
                    stage = 3
                    add_node(level, description, line, i)
                else:
                    # Unrecognized heading, infer level from # count
                    heading_level = len(line) - len(line.lstrip('#'))
                    if heading_level == 1:
                        # Try to categorize common sections
                        title = line.strip("# ").strip()
                        if any(keyword in title for keyword in
                              ["Preliminary", "Preliminaries", "Notation", "Problem"]):
                            add_node(1, "preliminaries", line, i)
                        elif any(keyword in title for keyword in
                                ["Limitation", "Future Work", "Future"]):
                            add_node(1, "limitations", line, i)
                        elif any(keyword in title for keyword in
                                ["Communication", "Implementation", "Analysis"]):
                            add_node(1, "section", line, i)
                        else:
                            add_node(1, "section", line, i)
                    elif heading_level == 2:
                        add_node(2, "subsection", line, i)
                    elif heading_level == 3:
                        add_node(3, "subsubsection", line, i)
                    else:
                        add_content(line)
            elif stage >= 2:
                add_content(line)

            i += 1

        return metadata, tree
