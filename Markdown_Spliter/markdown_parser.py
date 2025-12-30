from typing import Optional
from Markdown_Spliter.strategies import (
    ParsingStrategy,
    StrategyFactory,
    ThesisParsingStrategy,
    ConferencePaperStrategy,
    JournalPaperStrategy
)


class MarkdownParser:
    """
    Main parser class for Markdown documents.

    Uses a strategy pattern to support different document formats (thesis, conference papers, etc.).
    The parser automatically detects the document format or allows manual specification.

    Usage:
        # Automatic format detection
        parser = MarkdownParser.init_by_path("document.md")

        # Manual format specification
        parser = MarkdownParser.init_by_path("document.md", strategy="thesis")

        # From string
        parser = MarkdownParser.init_by_str(content)
        parser._parse()
    """

    def __init__(self, strategy: Optional[ParsingStrategy] = None):
        """
        Initialize the parser.

        Args:
            strategy: Optional parsing strategy instance. If None, will be auto-detected later.
        """
        self.metadata = {}
        self.content = None
        self.path = None
        self.lines = []
        self.parse_tree = []
        self.strategy = strategy
        # For backward compatibility
        self.keywords_config = strategy.keywords_config if strategy else []

    @classmethod
    def init_by_path(cls, path: str, strategy: Optional[str] = None, verbose: bool = False):
        """
        Initialize the parser with a file path.

        Args:
            path: Path to the markdown file
            strategy: Optional strategy name ("thesis", "conference", etc.)
                     If None, format will be auto-detected
            verbose: If True, print format detection information

        Returns:
            An instance of MarkdownParser with content loaded and parsed
        """
        instance = cls()
        instance.path = path
        instance._load_md(path)

        # Auto-detect or create strategy
        instance.strategy = StrategyFactory.create_strategy(
            strategy_name=strategy,
            content=instance.content,
            lines=instance.lines,
            verbose=verbose
        )
        instance.keywords_config = instance.strategy.keywords_config

        # Parse the document
        instance._parse()
        return instance

    @classmethod
    def init_by_str(cls, content: str, strategy: Optional[str] = None, verbose: bool = False):
        """
        Initialize the parser with a string.

        Args:
            content: Content of the markdown file
            strategy: Optional strategy name ("thesis", "conference", etc.)
                     If None, format will be auto-detected when _parse() is called
            verbose: If True, print format detection information

        Returns:
            An instance of MarkdownParser (note: you must call _parse() manually)
        """
        instance = cls()
        instance.content = content

        # Prepare lines for strategy detection
        lines = content.split("\n")
        instance.lines = [line for line in lines if line.strip() != ""]

        # Auto-detect or create strategy
        instance.strategy = StrategyFactory.create_strategy(
            strategy_name=strategy,
            content=instance.content,
            lines=instance.lines,
            verbose=verbose
        )
        instance.keywords_config = instance.strategy.keywords_config

        return instance

    def _load_md(self, path: str):
        """
        Load markdown content from a file.

        Args:
            path: Path to the markdown file
        """
        with open(path, "r", encoding="utf-8") as f:
            self.content = f.read()

        lines = self.content.split("\n")
        # Remove empty lines
        self.lines = [line for line in lines if line.strip() != ""]

    def get_metadata(self) -> dict:
        """
        Get metadata from the parsed document.

        Returns:
            A dictionary containing metadata
        """
        return self.metadata

    def get_parse_tree(self) -> list:
        """
        Get the parse tree of the markdown content.

        Returns:
            A list representing the parse tree
        """
        return self.parse_tree

    def _parse(self):
        """
        Parse the markdown content to extract metadata and structure.

        Delegates parsing to the selected strategy.
        """
        if self.strategy is None:
            raise RuntimeError("No parsing strategy set. Use init_by_path() or init_by_str() to initialize.")

        # Delegate parsing to the strategy
        metadata, parse_tree = self.strategy.parse(self.lines)

        self.metadata = metadata
        self.parse_tree = parse_tree

    def get_section_content(self, **kwargs) -> str:
        """
        Get specific sections and their content, returned as a Markdown string.

        Available query parameters:
            level: Heading level (1 = chapter, 2 = section, etc.)
            description: Description type ('chapter', 'section', 'abstract_ch', etc.)
            title: Title content (partial match)
            exact_title: Title content (exact match)

        Returns:
            Markdown-formatted string containing the matched sections and their content
        """
        if not hasattr(self, 'parse_tree') or not self.parse_tree:
            return ""

        # Find matching nodes
        found_nodes = self._find_nodes(self.parse_tree, **kwargs)

        if not found_nodes:
            return ""

        # Convert nodes to Markdown format
        result = ""
        for node in found_nodes:
            result += self._node_to_markdown(node)

        return result

    def _find_nodes(self, nodes: list, **kwargs) -> list:
        """
        Recursively find nodes matching the given criteria.

        Args:
            nodes: List of nodes to search
            kwargs: Query parameters

        Returns:
            List of matching nodes
        """
        found = []

        for node in nodes:
            # Check if node matches all specified criteria
            match = True

            for key, value in kwargs.items():
                if key == 'level' and 'level' in node and node['level'] != value:
                    match = False
                    break
                elif key == 'description' and 'description' in node and node['description'] != value:
                    match = False
                    break
                elif key == 'title' and 'title' in node and value not in node['title']:
                    match = False
                    break
                elif key == 'exact_title' and 'title' in node and value != node['title']:
                    match = False
                    break

            if match:
                found.append(node)

            # Recursively search child nodes
            if 'children' in node and node['children']:
                child_found = self._find_nodes(node['children'], **kwargs)
                found.extend(child_found)

        return found

    def _node_to_markdown(self, node: dict, depth: int = 0) -> str:
        """
        Convert a node to Markdown format.

        Args:
            node: Node to convert
            depth: Current depth (for nested heading levels)

        Returns:
            Markdown-formatted string
        """
        # Determine heading level based on node level
        heading_level = min(6, node['level'] + depth) if node['level'] > 0 else 1 + depth

        # Create Markdown heading
        md = '#' * heading_level + ' ' + node['title'] + '\n\n'

        # Add node content (if any)
        if node['content'].strip():
            md += node['content'].strip() + '\n\n'

        # Recursively add child nodes
        for child in node['children']:
            md += self._node_to_markdown(child, depth + 1)

        return md

    def get_strategy_name(self) -> str:
        """
        Get the name of the currently used parsing strategy.

        Returns:
            Strategy class name (e.g., "ThesisParsingStrategy")
        """
        if self.strategy:
            return self.strategy.get_name()
        return "None"


# Register all available strategies
StrategyFactory.register_strategy(ThesisParsingStrategy)
StrategyFactory.register_strategy(ConferencePaperStrategy)
StrategyFactory.register_strategy(JournalPaperStrategy)
