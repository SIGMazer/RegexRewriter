from .RegexRewriter import RegexRewriter

defaultrw = RegexRewriter()

rewrite = defaultrw.rewrite

__all__ = ['rewrite', 'RegexRewriter']
