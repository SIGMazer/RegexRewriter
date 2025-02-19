# Regex Rewriter

## Overview

The Regex Rewriter is a tool designed to manipulate text based on regular expressions.

## Installation

```bash
pip install RegexRewriter
```

## Usage 

```python
from RegexRewriter import RegexRewriter

rewriter = RegexRewriter()
print(rewriter.rewrite("hello", r"[a-z]{3}[A-Z]{2}"))  # Should output: helLO
print(rewriter.rewrite("test", r"[0-9]{2}[a-z]{2}"))  # Should output: 00es or similar
print(rewriter.rewrite("hello", r"^pre_[A-Z][a-z]+$"))  # Should output: pre_Hello
print(rewriter.rewrite("hello world", r"^[A-Z][a-z]+ [a-z]+$"))  # Should output: Hello world
print(rewriter.rewrite("example", r"https?:\/\/[\w\-\.]+\.[a-z]{2,}"))  # Should add protocol & TLD
print(rewriter.rewrite("wrong", r"(right|correct|valid)"))  # Should transform to one of the alternatives
```

## License

This project is open-source and available for modification and distribution under the [MIT](https://github.com/SIGMazer/RegexRewriter/blob/main/LICENSE) license.
