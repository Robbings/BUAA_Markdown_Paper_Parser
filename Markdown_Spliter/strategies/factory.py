from typing import List, Optional, Type
from .base import ParsingStrategy


class StrategyFactory:
    """
    Factory class for automatically detecting and creating the appropriate parsing strategy.

    The factory uses an intelligent scoring algorithm to determine which parsing strategy
    best matches the document format.
    """

    # Registry of available strategies
    _strategies: List[Type[ParsingStrategy]] = []

    # Minimum confidence threshold for auto-detection
    CONFIDENCE_THRESHOLD = 0.3

    @classmethod
    def register_strategy(cls, strategy_class: Type[ParsingStrategy]):
        """
        Register a parsing strategy with the factory.

        Args:
            strategy_class: A subclass of ParsingStrategy
        """
        if not issubclass(strategy_class, ParsingStrategy):
            raise TypeError(f"{strategy_class} must be a subclass of ParsingStrategy")

        if strategy_class not in cls._strategies:
            cls._strategies.append(strategy_class)

    @classmethod
    def unregister_strategy(cls, strategy_class: Type[ParsingStrategy]):
        """
        Unregister a parsing strategy from the factory.

        Args:
            strategy_class: A subclass of ParsingStrategy
        """
        if strategy_class in cls._strategies:
            cls._strategies.remove(strategy_class)

    @classmethod
    def get_registered_strategies(cls) -> List[Type[ParsingStrategy]]:
        """
        Get all registered parsing strategies.

        Returns:
            List of registered strategy classes
        """
        return cls._strategies.copy()

    @classmethod
    def auto_detect(cls, content: str, lines: List[str], verbose: bool = False) -> ParsingStrategy:
        """
        Automatically detect the document format and return the appropriate parsing strategy.

        Uses a confidence-based scoring system:
        1. Each registered strategy evaluates the document and returns a confidence score (0-1)
        2. The strategy with the highest score above the threshold is selected
        3. If no strategy meets the threshold, the first registered strategy is used as default

        Args:
            content: Full document content as string
            lines: Document split into non-empty lines
            verbose: If True, print detection scores for debugging

        Returns:
            An instance of the best-matching ParsingStrategy
        """
        if not cls._strategies:
            raise RuntimeError("No parsing strategies registered. Please register at least one strategy.")

        scores = {}

        # Evaluate all strategies
        for strategy_class in cls._strategies:
            strategy_instance = strategy_class()
            score = strategy_instance.detect(content, lines)
            scores[strategy_class] = score

            if verbose:
                print(f"{strategy_instance.get_name()}: {score:.3f}")

        # Find the strategy with the highest score
        best_strategy_class = max(scores, key=scores.get)
        best_score = scores[best_strategy_class]

        if verbose:
            print(f"\nSelected: {best_strategy_class.__name__} (score: {best_score:.3f})")

        # Check if the best score meets the threshold
        if best_score < cls.CONFIDENCE_THRESHOLD:
            if verbose:
                print(f"Warning: Best score {best_score:.3f} is below threshold {cls.CONFIDENCE_THRESHOLD}")
                print(f"Using {best_strategy_class.__name__} as default")

        return best_strategy_class()

    @classmethod
    def create_strategy(cls, strategy_name: Optional[str], content: str, lines: List[str],
                       verbose: bool = False) -> ParsingStrategy:
        """
        Create a parsing strategy instance.

        Args:
            strategy_name: Name of the strategy to use, or None for auto-detection
                          Supported formats: "thesis", "ThesisParsingStrategy", etc.
            content: Full document content as string
            lines: Document split into non-empty lines
            verbose: If True, print detection information

        Returns:
            An instance of ParsingStrategy

        Raises:
            ValueError: If the specified strategy name is not found
        """
        # Auto-detection if no strategy name provided
        if strategy_name is None:
            return cls.auto_detect(content, lines, verbose)

        # Normalize strategy name (case-insensitive, with or without "Strategy" suffix)
        strategy_name_lower = strategy_name.lower()

        # Try to find matching strategy
        for strategy_class in cls._strategies:
            class_name_lower = strategy_class.__name__.lower()

            # Generate all possible simplified variations
            # "ThesisParsingStrategy" -> ["thesis", "thesisparsing", "thesisparsingstrategy", ...]
            # "ConferencePaperStrategy" -> ["conference", "conferencepaper", "conferencestr", ...]
            # "JournalPaperStrategy" -> ["journal", "journalpaper", "journalstr", ...]
            simplified_names = set([
                class_name_lower,  # Full name
                class_name_lower.replace("parsingstrategy", ""),  # Remove "parsingstrategy"
                class_name_lower.replace("strategy", ""),  # Remove "strategy"
                class_name_lower.replace("paperstrategy", ""),  # Remove "paperstrategy"
                class_name_lower.replace("paper", ""),  # Remove "paper"
            ])

            # Also add the most simplified version (first word)
            # "conferencepaperstrategy" -> "conference"
            # "journalpaperstrategy" -> "journal"
            for sep in ["paper", "parsing", "strategy"]:
                parts = class_name_lower.split(sep)
                if parts:
                    simplified_names.add(parts[0])

            # Match by any variation
            if strategy_name_lower in simplified_names:
                if verbose:
                    print(f"Using specified strategy: {strategy_class.__name__}")
                return strategy_class()

        # Strategy not found
        available = [s.__name__ for s in cls._strategies]
        raise ValueError(f"Strategy '{strategy_name}' not found. Available strategies: {available}")

    @classmethod
    def set_confidence_threshold(cls, threshold: float):
        """
        Set the minimum confidence threshold for auto-detection.

        Args:
            threshold: Confidence threshold (0.0 to 1.0)

        Raises:
            ValueError: If threshold is not in valid range
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}")

        cls.CONFIDENCE_THRESHOLD = threshold
