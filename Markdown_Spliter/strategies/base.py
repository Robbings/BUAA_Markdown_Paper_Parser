from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any
import re


class ParsingStrategy(ABC):
    """
    Abstract base class for parsing strategies.

    Each parsing strategy represents a different document format (e.g., thesis, conference paper, journal paper).
    Strategies are responsible for:
    1. Detecting whether a document matches their format
    2. Defining format-specific keyword configurations
    3. Implementing format-specific parsing logic (if needed)
    """

    def __init__(self):
        """Initialize the parsing strategy with its keyword configuration."""
        self.keywords_config = self._define_keywords_config()

    @abstractmethod
    def _define_keywords_config(self) -> List[Dict[str, Any]]:
        """
        Define the keyword configuration for this document format.

        Returns:
            List of dictionaries, each containing:
                - keyword: regex pattern to match
                - description: semantic type (e.g., "chapter", "abstract")
                - level: hierarchical level (-1 for metadata, 1+ for content)
        """
        pass

    @abstractmethod
    def get_detection_features(self) -> Dict[str, Any]:
        """
        Define the features used to detect this document format.

        Returns:
            Dictionary containing:
                - required_patterns: List of (pattern, weight) tuples that should appear
                - optional_patterns: List of (pattern, weight) tuples that add confidence
                - structural_hints: List of (hint_function, weight) tuples for structural analysis
                - exclusion_patterns: List of patterns that indicate this is NOT the right format
        """
        pass

    def detect(self, content: str, lines: List[str]) -> float:
        """
        Detect whether the document matches this format.

        Uses an intelligent scoring algorithm based on:
        1. Required pattern matching (high weight)
        2. Optional pattern matching (medium weight)
        3. Structural analysis (variable weight)
        4. Exclusion patterns (negative scoring)

        Args:
            content: Full document content as string
            lines: Document split into lines (non-empty lines)

        Returns:
            Confidence score between 0.0 (no match) and 1.0 (perfect match)
        """
        features = self.get_detection_features()

        # Initialize score and max possible score
        score = 0.0
        max_score = 0.0

        # Check exclusion patterns first (early exit if found)
        exclusion_patterns = features.get('exclusion_patterns', [])
        for pattern in exclusion_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                return 0.0  # Immediate disqualification

        # Check required patterns
        required_patterns = features.get('required_patterns', [])
        for pattern, weight in required_patterns:
            max_score += weight
            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                score += weight
            else:
                # Missing a required pattern significantly reduces confidence
                score -= weight * 0.5

        # Check optional patterns
        optional_patterns = features.get('optional_patterns', [])
        for pattern, weight in optional_patterns:
            max_score += weight
            # Count occurrences for better scoring
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                # Give partial credit based on match count (up to full weight)
                occurrence_score = min(len(matches) / 3.0, 1.0) * weight
                score += occurrence_score

        # Check structural hints
        structural_hints = features.get('structural_hints', [])
        for hint_function, weight in structural_hints:
            max_score += weight
            hint_score = hint_function(content, lines)
            score += hint_score * weight

        # Normalize score to 0-1 range
        if max_score > 0:
            normalized_score = max(0.0, min(1.0, score / max_score))
        else:
            normalized_score = 0.0

        return normalized_score

    def parse(self, lines: List[str]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Parse the document content into metadata and parse tree.

        By default, uses the generic state machine parser.
        Subclasses can override this method to implement custom parsing logic.

        Args:
            lines: List of non-empty lines from the document

        Returns:
            Tuple of (metadata, parse_tree)
                - metadata: Dictionary containing document metadata
                - parse_tree: List of nodes representing document structure
        """
        return self._generic_parse(lines)

    def _match_keyword_level(self, text: str) -> Tuple[int, str]:
        """
        Match keywords in the text to determine their level and description.

        Args:
            text: Text to be matched

        Returns:
            Tuple of (level, description) or (None, None) if no match
        """
        for config in self.keywords_config:
            if re.search(config["keyword"], text):
                return config["level"], config["description"]
        return None, None

    def _generic_parse(self, lines: List[str]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Generic parsing implementation using a state machine.

        This is the default implementation that works for most document types.
        Subclasses can override parse() to provide custom logic.

        Args:
            lines: List of non-empty lines from the document

        Returns:
            Tuple of (metadata, parse_tree)
        """
        metadata = {}
        tree = []
        node_stack = []

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

        def add_content(line):
            if node_stack:
                node_stack[-1]["content"] += line.strip() + "\n"

        # Simple generic parsing: identify headings and build tree
        for i, line in enumerate(lines):
            line = line.strip()

            if line.startswith("#"):
                level, description = self._match_keyword_level(line)
                if level is not None:
                    add_node(level, description, line, i)
                else:
                    add_content(line)
            else:
                add_content(line)

        return metadata, tree

    def get_name(self) -> str:
        """
        Get the name of this parsing strategy.

        Returns:
            Strategy name (e.g., "ThesisParsingStrategy")
        """
        return self.__class__.__name__
