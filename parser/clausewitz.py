"""
Clausewitz Engine Script Parser

Parses Paradox game script files (.txt) into Python dictionaries.
Handles the nested brace syntax used in EU5 and other Clausewitz games.
"""

import re
from pathlib import Path
from typing import Any, Union


class ClausewitzParser:
    """Parser for Clausewitz engine script files."""

    def __init__(self):
        self.pos = 0
        self.text = ""
        self.length = 0

    def parse_file(self, filepath: Union[str, Path]) -> dict:
        """Parse a single file and return its contents as a dictionary."""
        filepath = Path(filepath)

        # Read file with UTF-8-BOM handling
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        return self.parse(content)

    def parse(self, text: str) -> dict:
        """Parse text content and return as dictionary."""
        # Remove comments
        text = self._remove_comments(text)

        self.text = text
        self.length = len(text)
        self.pos = 0

        return self._parse_block()

    def _remove_comments(self, text: str) -> str:
        """Remove # comments from text."""
        lines = text.split('\n')
        result = []
        for line in lines:
            # Find # not inside quotes
            in_quote = False
            comment_pos = -1
            for i, char in enumerate(line):
                if char == '"':
                    in_quote = not in_quote
                elif char == '#' and not in_quote:
                    comment_pos = i
                    break

            if comment_pos >= 0:
                result.append(line[:comment_pos])
            else:
                result.append(line)

        return '\n'.join(result)

    def _skip_whitespace(self):
        """Skip whitespace characters."""
        while self.pos < self.length and self.text[self.pos] in ' \t\n\r':
            self.pos += 1

    def _peek(self) -> str:
        """Look at current character without consuming."""
        if self.pos >= self.length:
            return ''
        return self.text[self.pos]

    def _read_token(self) -> str:
        """Read the next token (identifier, number, or quoted string)."""
        self._skip_whitespace()

        if self.pos >= self.length:
            return ''

        char = self.text[self.pos]

        # Single character tokens
        if char in '{}=<>':
            self.pos += 1
            # Handle >=, <=, ==
            if char in '<>=' and self.pos < self.length and self.text[self.pos] == '=':
                self.pos += 1
                return char + '='
            return char

        # Handle != operator
        if char == '!' and self.pos + 1 < self.length and self.text[self.pos + 1] == '=':
            self.pos += 2
            return '!='

        # Handle ?= operator (null-safe equals)
        if char == '?' and self.pos + 1 < self.length and self.text[self.pos + 1] == '=':
            self.pos += 2
            return '?='

        # Quoted string
        if char == '"':
            return self._read_quoted_string()

        # Identifier or number
        return self._read_identifier()

    def _read_quoted_string(self) -> str:
        """Read a quoted string."""
        self.pos += 1  # Skip opening quote
        start = self.pos

        while self.pos < self.length:
            if self.text[self.pos] == '"':
                result = self.text[start:self.pos]
                self.pos += 1  # Skip closing quote
                return result
            self.pos += 1

        # Unclosed quote - return what we have
        return self.text[start:]

    def _read_identifier(self) -> str:
        """Read an identifier (alphanumeric + underscores, colons, dots, etc.)."""
        start = self.pos

        while self.pos < self.length:
            char = self.text[self.pos]
            # Allow alphanumeric, underscore, colon, dot, minus, at sign
            if char.isalnum() or char in '_:.-@':
                self.pos += 1
            else:
                break

        return self.text[start:self.pos]

    def _parse_block(self) -> dict:
        """Parse a block (contents between braces or top-level)."""
        result = {}

        while True:
            self._skip_whitespace()

            if self.pos >= self.length:
                break

            char = self._peek()

            if char == '}':
                self.pos += 1  # Consume closing brace
                break

            if char == '{':
                # Anonymous block - shouldn't happen at this level normally
                self.pos += 1
                self._parse_block()  # Skip it
                continue

            # Read key
            key = self._read_token()
            if not key:
                break

            self._skip_whitespace()

            # Check what follows
            next_char = self._peek()

            if next_char == '=':
                self.pos += 1  # Consume =
                self._skip_whitespace()
                # Check for == (equality comparison)
                if self._peek() == '=':
                    self.pos += 1
                    self._skip_whitespace()
                    value = self._parse_value()
                    result[key] = {'_op': '==', '_value': value}
                else:
                    value = self._parse_value()

                    # Handle duplicate keys by converting to list
                    if key in result:
                        existing = result[key]
                        if isinstance(existing, list):
                            existing.append(value)
                        else:
                            result[key] = [existing, value]
                    else:
                        result[key] = value

            elif next_char in '!?<>':
                # Comparison operator (>=, <=, >, <, !=, ?=)
                op = self._read_token()
                self._skip_whitespace()
                value = self._parse_value()
                # Store as special comparison dict
                result[key] = {'_op': op, '_value': value}

            elif next_char == '{':
                # Key followed directly by block (no =)
                self.pos += 1
                value = self._parse_block()
                if key in result:
                    existing = result[key]
                    if isinstance(existing, list):
                        existing.append(value)
                    else:
                        result[key] = [existing, value]
                else:
                    result[key] = value

            else:
                # Key with no value - treat as flag (true)
                result[key] = True

        return result

    def _parse_value(self) -> Any:
        """Parse a value (block, list, or scalar)."""
        self._skip_whitespace()

        char = self._peek()

        if char == '{':
            self.pos += 1
            # Could be a block or a simple list
            return self._parse_block_or_list()

        # Scalar value
        token = self._read_token()

        # Try to convert to appropriate type
        return self._convert_value(token)

    def _parse_block_or_list(self) -> Any:
        """Parse either a block (key=value pairs) or a list (bare values)."""
        items = []
        is_list = None

        while True:
            self._skip_whitespace()

            if self.pos >= self.length:
                break

            char = self._peek()

            if char == '}':
                self.pos += 1
                break

            if char == '{':
                # Nested block in a list
                self.pos += 1
                items.append(self._parse_block())
                if is_list is None:
                    is_list = True
                continue

            # Read first token
            token = self._read_token()
            if not token:
                break

            self._skip_whitespace()
            next_char = self._peek()

            if next_char == '=' or next_char in '<>':
                # This is a key=value pair, so it's a block
                if is_list is True:
                    # Mixed content - treat previous items as special
                    pass
                is_list = False

                if next_char == '=':
                    self.pos += 1
                    self._skip_whitespace()
                    value = self._parse_value()
                else:
                    op = self._read_token()
                    self._skip_whitespace()
                    value = self._parse_value()
                    value = {'_op': op, '_value': value}

                items.append((token, value))
            else:
                # Bare value - this is a list
                if is_list is False:
                    # We already have key=value pairs, treat this as unusual
                    items.append((token, True))
                else:
                    is_list = True
                    items.append(self._convert_value(token))

        # Return appropriate type
        if is_list is True or is_list is None:
            return items if items else {}
        else:
            # Convert list of tuples to dict
            result = {}
            for item in items:
                if isinstance(item, tuple):
                    key, value = item
                    if key in result:
                        existing = result[key]
                        if isinstance(existing, list):
                            existing.append(value)
                        else:
                            result[key] = [existing, value]
                    else:
                        result[key] = value
            return result

    def _convert_value(self, token: str) -> Any:
        """Convert a string token to appropriate Python type."""
        if not token:
            return token

        # Boolean
        if token.lower() == 'yes':
            return True
        if token.lower() == 'no':
            return False

        # Number (int or float)
        try:
            if '.' in token:
                return float(token)
            return int(token)
        except ValueError:
            pass

        # String
        return token


def parse_file(filepath: Union[str, Path]) -> dict:
    """Convenience function to parse a file."""
    parser = ClausewitzParser()
    return parser.parse_file(filepath)


def parse_all_in_directory(dirpath: Union[str, Path], pattern: str = "*.txt") -> dict:
    """Parse all matching files in a directory, combining results."""
    dirpath = Path(dirpath)
    combined = {}

    for filepath in sorted(dirpath.glob(pattern)):
        try:
            data = parse_file(filepath)
            combined.update(data)
        except Exception as e:
            print(f"Warning: Failed to parse {filepath}: {e}")

    return combined


if __name__ == "__main__":
    # Test with a sample file
    import sys
    if len(sys.argv) > 1:
        result = parse_file(sys.argv[1])
        import json
        print(json.dumps(result, indent=2, default=str))
