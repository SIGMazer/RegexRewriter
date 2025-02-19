from dataclasses import dataclass
from typing import List, Set, Optional, Tuple, Dict, Union
import string
import re

@dataclass
class Component:
    """Represents a component of the regex pattern"""
    type: str  # 'char_class', 'literal', 'quantifier', 'anchor', 'alternation', 'group'
    value: Union[Set[str], List['Component'], str]  # Set for char_class, List for alternation/group
    min_repeat: int = 1
    max_repeat: int = 1
    is_anchor: bool = False
    anchor_type: Optional[str] = None  # 'start', 'end', 'boundary'
    group_type: Optional[str] = None  # 'capturing', 'non-capturing', 'lookahead', 'lookbehind'

class ImpossiblePatternError(Exception):
    pass

class RegexAnalyzer:
    def __init__(self):
        self.special_chars = '.^$*+?{}[]\\|()'
        
    def _parse_char_class(self, pattern: str, pos: int) -> Tuple[Component, int]:
        if pos >= len(pattern) or pattern[pos] != '[':
            raise ValueError("Expected '['")
            
        end_pos = pattern.find(']', pos)
        if end_pos == -1:
            raise ValueError("Unclosed character class")
            
        class_content = pattern[pos+1:end_pos]
        negated = class_content.startswith('^')
        if negated:
            class_content = class_content[1:]
            
        allowed_chars = set()
        i = 0
        while i < len(class_content):
            if i + 2 < len(class_content) and class_content[i + 1] == '-':
                start = class_content[i]
                end = class_content[i + 2]
                allowed_chars.update(chr(x) for x in range(ord(start), ord(end) + 1))
                i += 3
            else:
                allowed_chars.add(class_content[i])
                i += 1
                
        return Component('char_class', 
                        allowed_chars if not negated else set(string.printable) - allowed_chars), end_pos + 1

    def _parse_quantifier(self, pattern: str, pos: int) -> Tuple[int, float, int]:
        if pos >= len(pattern):
            return 1, 1, pos
            
        char = pattern[pos]
        if char == '*':
            return 0, float('inf'), pos + 1
        elif char == '+':
            return 1, float('inf'), pos + 1
        elif char == '?':
            return 0, 1, pos + 1
        elif char == '{':
            end_pos = pattern.find('}', pos)
            if end_pos == -1:
                raise ValueError("Unclosed quantifier")
            quantities = pattern[pos+1:end_pos].split(',')
            if len(quantities) == 1:
                min_q = max_q = int(quantities[0])
            else:
                min_q = int(quantities[0]) if quantities[0] else 0
                max_q = float('inf') if not quantities[1].strip() else int(quantities[1])
            return min_q, max_q, end_pos + 1
        
        return 1, 1, pos

    def _parse_group(self, pattern: str, pos: int) -> Tuple[Component, int]:
        """Parse a group (expression within parentheses)"""
        if pos >= len(pattern) or pattern[pos] != '(':
            raise ValueError("Expected '('")
            
        group_type = 'capturing'
        group_start = pos + 1
        
        # Check for non-capturing group (?:...)
        if pos+2 < len(pattern) and pattern[pos:pos+3] == '(?:':
            group_type = 'non-capturing'
            group_start = pos + 3
        # Positive lookahead (?=...)
        elif pos+2 < len(pattern) and pattern[pos:pos+3] == '(?=':
            group_type = 'positive_lookahead'
            group_start = pos + 3
        # Negative lookahead (?!...)
        elif pos+2 < len(pattern) and pattern[pos:pos+3] == '(?!':
            group_type = 'negative_lookahead'
            group_start = pos + 3
        # Positive lookbehind (?<=...)
        elif pos+3 < len(pattern) and pattern[pos:pos+4] == '(?<=':
            group_type = 'positive_lookbehind'
            group_start = pos + 4
        # Negative lookbehind (?<!...)
        elif pos+3 < len(pattern) and pattern[pos:pos+4] == '(?<!':
            group_type = 'negative_lookbehind'
            group_start = pos + 4
        
        paren_count = 1
        i = group_start
        while i < len(pattern) and paren_count > 0:
            if pattern[i] == '\\' and i + 1 < len(pattern):
                i += 2  
                continue
            if pattern[i] == '(':
                paren_count += 1
            elif pattern[i] == ')':
                paren_count -= 1
            i += 1
            
        if paren_count > 0:
            raise ValueError("Unclosed group")
            
        end_pos = i
        group_content = pattern[group_start:end_pos-1]
        
        group_components = self.analyze(group_content)
        
        return Component('group', group_components, 
                        group_type=group_type), end_pos
                
    def _parse_alternation(self, pattern: str) -> List[Component]:
        """Parse pattern with alternation (|) operator"""
        if '|' not in pattern:
            return self._parse_sequence(pattern)
            
        alternatives = []
        current_pos = 0
        start_pos = 0
        paren_depth = 0
        
        while current_pos < len(pattern):
            char = pattern[current_pos]
            
            if char == '\\' and current_pos + 1 < len(pattern):
                current_pos += 2  # Skip escaped character
                continue
                
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == '|' and paren_depth == 0:
                # Found an alternation at the top level
                alternatives.append(self._parse_sequence(pattern[start_pos:current_pos]))
                start_pos = current_pos + 1
                
            current_pos += 1
            
        # Add the last alternative
        alternatives.append(self._parse_sequence(pattern[start_pos:]))
        
        # Create an alternation component that contains lists of components
        all_alternatives = []
        for alt_components in alternatives:
            all_alternatives.append(alt_components)
            
        return [Component('alternation', all_alternatives)]
                
    def _parse_sequence(self, pattern: str) -> List[Component]:
        """Parse a sequence of components (no top-level alternation)"""
        components = []
        i = 0
        
        while i < len(pattern):
            char = pattern[i]
                
            if char == '[':
                component, i = self._parse_char_class(pattern, i)
            elif char == '(':
                component, i = self._parse_group(pattern, i)
            elif char == '\\':
                if i + 1 >= len(pattern):
                    raise ValueError("Incomplete escape sequence")
                    
                next_char = pattern[i + 1]
                if next_char == 'w':
                    allowed_chars = set(string.ascii_letters + string.digits + '_')
                elif next_char == 'd':
                    allowed_chars = set(string.digits)
                elif next_char == 's':
                    allowed_chars = set(' \t\n\r\f\v')
                elif next_char == 'W':
                    allowed_chars = set(string.printable) - set(string.ascii_letters + string.digits + '_')
                elif next_char == 'D':
                    allowed_chars = set(string.printable) - set(string.digits)
                elif next_char == 'S':
                    allowed_chars = set(string.printable) - set(' \t\n\r\f\v')
                elif next_char == 'b':
                    component = Component('anchor', set(), is_anchor=True, anchor_type='word_boundary')
                    i += 2
                    components.append(component)
                    continue
                elif next_char == 'B':
                    component = Component('anchor', set(), is_anchor=True, anchor_type='non_word_boundary')
                    i += 2
                    components.append(component)
                    continue
                else:
                    allowed_chars = {next_char}
                    
                component = Component('char_class', allowed_chars)
                i += 2
            elif char == '.':
                # Dot matches any character except newline
                allowed_chars = set(string.printable) - {'\n'}
                component = Component('char_class', allowed_chars)
                i += 1
            elif char == '^':
                component = Component('anchor', set(), is_anchor=True, anchor_type='start')
                i += 1
                components.append(component)
                continue
            elif char == '$':
                component = Component('anchor', set(), is_anchor=True, anchor_type='end')
                i += 1
                components.append(component)
                continue
            else:
                component = Component('literal', {char})
                i += 1
                
            # Check for quantifier
            if i < len(pattern) and pattern[i] in '*+?{':
                min_repeat, max_repeat, i = self._parse_quantifier(pattern, i)
                component.min_repeat = min_repeat
                component.max_repeat = max_repeat
                
            components.append(component)
                
        return components

    def analyze(self, pattern: str) -> List[Component]:
        return self._parse_alternation(pattern)

class RegexRewriter:
    def __init__(self, max_insertions=10):
        self.analyzer = RegexAnalyzer()
        self.max_insertions = max_insertions
        
    def _char_matches_component(self, char: str, component: Component) -> bool:
        if component.type == 'char_class':
            return char in component.value
        elif component.type == 'literal':
            return char in component.value
        return False
        
    def _transform_char(self, char: str, allowed_chars: Set[str]) -> Optional[str]:
        if char in allowed_chars:
            return char
            
        if char.isupper():
            lower_char = char.lower()
            if lower_char in allowed_chars:
                return lower_char
        elif char.islower():
            upper_char = char.upper()
            if upper_char in allowed_chars:
                return upper_char
        
        return None
    
    def _choose_insertion_char(self, component: Component) -> str:
        if component.type == 'char_class':
            for char in 'aeiouAEIOU0123456789_-':
                if char in component.value:
                    return char
                    
            return next(iter(component.value))
        elif component.type == 'literal':
            return next(iter(component.value))
        else:
            return 'a'
    
    def _get_pattern_length_range(self, components: List[Component]) -> Tuple[int, int]:
        content_components = [comp for comp in components if not comp.is_anchor]
        
        min_length = 0
        max_length = 0
        
        for comp in content_components:
            if comp.type == 'alternation':
                alt_mins = []
                alt_maxs = []
                for alt in comp.value:
                    alt_min, alt_max = self._get_pattern_length_range(alt)
                    alt_mins.append(alt_min)
                    alt_maxs.append(alt_max)
                min_length += min(alt_mins) if alt_mins else 0
                if float('inf') in alt_maxs:
                    max_length = float('inf')
                else:
                    max_length += max(alt_maxs) if alt_maxs else 0
            elif comp.type == 'group':
                group_min, group_max = self._get_pattern_length_range(comp.value)
                min_length += group_min * comp.min_repeat
                if comp.max_repeat == float('inf'):
                    max_length = float('inf')
                else:
                    if group_max == float('inf'):
                        max_length = float('inf')
                    else:
                        max_length += group_max * comp.max_repeat
            else:
                min_length += comp.min_repeat
                if comp.max_repeat == float('inf'):
                    max_length = float('inf')
                else:
                    max_length += comp.max_repeat
                    
        return min_length, max_length
        
    def _handle_alternation(self, component: Component, input_string: str, remaining_insertions: int) -> Tuple[str, int]:
        """Handle alternation by trying each alternative"""
        alternatives = component.value  # List of lists of components
        
        for alt_components in alternatives:
            try:
                result, insertions_used = self._process_components(
                    input_string, alt_components, remaining_insertions)
                return result, insertions_used
            except ImpossiblePatternError:
                continue
                
        try:
            shortest_alt = min(alternatives, key=len)
            return self._process_components(input_string, shortest_alt, remaining_insertions)
        except:
            return input_string, 0
        
    def _handle_group(self, component: Component, input_string: str,
                      remaining_insertions: int) -> Tuple[str, int]:

        inner_components = component.value
        group_type = component.group_type
        
        if group_type and group_type.endswith(('lookahead', 'lookbehind')):
            return input_string, 0
            
        return self._process_components(input_string, inner_components, remaining_insertions)
    
    def _process_components(self, input_string: str, components: List[Component], 
                           remaining_insertions: int) -> Tuple[str, int]:
        
        result = list(input_string)
        input_pos = 0
        result_pos = 0
        initial_insertions = remaining_insertions
        
        component_idx = 0
        while component_idx < len(components):
            component = components[component_idx]
            
            if component.is_anchor:
                component_idx += 1
                continue
                
            if component.type == 'alternation':
                segment = input_string[input_pos:] if input_pos < len(input_string) else ""
                alt_result, insertions_used = self._handle_alternation(
                    component, segment, remaining_insertions)
                
                for i, c in enumerate(alt_result):
                    if result_pos + i < len(result):
                        result[result_pos + i] = c
                    else:
                        result.append(c)
                
                result_pos += len(alt_result)
                input_pos += min(len(alt_result), len(segment))
                remaining_insertions -= insertions_used
                
            elif component.type == 'group':
                segment = input_string[input_pos:] if input_pos < len(input_string) else ""
                group_result, insertions_used = self._handle_group(
                    component, segment, remaining_insertions)
                
                for i, c in enumerate(group_result):
                    if result_pos + i < len(result):
                        result[result_pos + i] = c
                    else:
                        result.append(c)
                
                result_pos += len(group_result)
                input_pos += min(len(group_result), len(segment))
                remaining_insertions -= insertions_used
                
            else:
                chars_processed = 0
                insertions_used = 0
                
                for _ in range(component.min_repeat):
                    if input_pos < len(input_string):
                        if component.type in ('char_class', 'literal'):
                            transformed = self._transform_char(input_string[input_pos], component.value)
                        else:
                            transformed = None
                        
                        if transformed is not None:
                            # Character was transformable
                            if result_pos < len(result):
                                result[result_pos] = transformed
                            else:
                                result.append(transformed)
                            input_pos += 1
                            result_pos += 1
                            chars_processed += 1
                        elif remaining_insertions > 0:
                            insert_char = self._choose_insertion_char(component)
                            if result_pos < len(result):
                                result.insert(result_pos, insert_char)
                            else:
                                result.append(insert_char)
                            result_pos += 1
                            remaining_insertions -= 1
                            insertions_used += 1
                            chars_processed += 1
                        else:
                            raise ImpossiblePatternError("Cannot transform character and no insertions left")
                    elif remaining_insertions > 0:
                        insert_char = self._choose_insertion_char(component)
                        result.append(insert_char)
                        result_pos += 1
                        remaining_insertions -= 1
                        insertions_used += 1
                        chars_processed += 1
                    else:
                        raise ImpossiblePatternError("Input too short and no insertions left")
                
                max_additional = component.max_repeat - component.min_repeat
                additional_processed = 0
                
                while ((component.max_repeat == float('inf') or 
                       additional_processed < max_additional) and
                       input_pos < len(input_string)):
                    
                    if component.type in ('char_class', 'literal'):
                        transformed = self._transform_char(input_string[input_pos], component.value)
                    else:
                        transformed = None
                        
                    if transformed is not None:
                        if result_pos < len(result):
                            result[result_pos] = transformed
                        else:
                            result.append(transformed)
                        input_pos += 1
                        result_pos += 1
                        chars_processed += 1
                        additional_processed += 1
                    else:
                        break
            
            component_idx += 1
        
        insertions_used = initial_insertions - remaining_insertions
        
        return ''.join(result[:result_pos]), insertions_used
        
    def rewrite(self, input_string: str, pattern: str) -> str:
        if re.fullmatch(pattern, input_string):
            return input_string
            
        try:
            components = self.analyzer.analyze(pattern)
        except ValueError as e:
            return input_string
            
        has_start_anchor = any(comp.is_anchor and comp.anchor_type == 'start' for comp in components)
        has_end_anchor = any(comp.is_anchor and comp.anchor_type == 'end' for comp in components)
        
        prefix = ""
        prefix_components = []
        
        if has_start_anchor:
            component_idx = 0
            while component_idx < len(components):
                comp = components[component_idx]
                if comp.is_anchor and comp.anchor_type == 'start':
                    component_idx += 1
                    continue
                    
                if comp.type == 'literal':
                    for _ in range(comp.min_repeat):
                        prefix += next(iter(comp.value))
                    prefix_components.append(comp)
                    component_idx += 1
                else:
                    break
        
        content_components = [comp for comp in components if comp not in prefix_components and not (comp.is_anchor and comp.anchor_type == 'start')]
        
        try:
            if prefix:
                processed_content, _ = self._process_components(input_string, content_components, self.max_insertions)
                result = prefix + processed_content
            else:
                result, _ = self._process_components(input_string, components, self.max_insertions)
                
            if re.fullmatch(pattern, result):
                return result
                
            if has_end_anchor and not re.fullmatch(pattern, result):
                for i in range(len(result), 0, -1):
                    truncated = result[:i]
                    if re.fullmatch(pattern, truncated):
                        return truncated
            
            if not re.fullmatch(pattern, result):
                if has_start_anchor and pattern.startswith('^'):
                    literal_part = pattern[1:]
                    if has_end_anchor and literal_part.endswith('$'):
                        literal_part = literal_part[:-1]
                        
                    if all(c not in self.analyzer.special_chars for c in literal_part):
                        return literal_part
                
            return result
            
        except ImpossiblePatternError:
            if pattern.startswith('^') and pattern.endswith('$'):
                literal_part = pattern[1:-1]
                if all(c not in self.analyzer.special_chars for c in literal_part):
                    return literal_part
            
            return input_string

