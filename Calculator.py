import pygame
import sys
import math
import clipboard
import re
from datetime import datetime

pygame.init()

# Constants
WIDTH, HEIGHT = 400, 600
BUTTON_WIDTH, BUTTON_HEIGHT = 88, 60
BUTTON_MARGIN = 10
TOP_OFFSET = 170
MAX_CHARS_PER_LINE = 22
LINE_HEIGHT = 40
HISTORY_ITEM_PADDING = 10
ANIMATION_SPEED = 15
HISTORY_SCROLLBAR_WIDTH = 8
HISTORY_THUMB_MIN_HEIGHT = 30

THEMES = {
    "light": {
        "bg": (122, 176, 223),
        "button": (255, 255, 255),
        "button2": (200, 200, 200),
        "text": (0, 0, 0),
        "display": (240, 240, 240),
        "selection": (0, 120, 215, 100),
        "outline": (100, 100, 255),
        "scrollbar": (200, 200, 200),
        "thumb": (100, 100, 100),
        "history_bg": (220, 220, 220),
        "history_item": (240, 240, 240),
    },
    "dark": {
        "bg": (34, 34, 34),
        "button": (60, 60, 60),
        "button2": (128, 128, 128),
        "text": (255, 255, 255),
        "display": (25, 25, 25),
        "selection": (0, 120, 215, 100),
        "outline": (140, 140, 255),
        "scrollbar": (90, 90, 90),
        "thumb": (150, 150, 150),
        "history_bg": (50, 50, 50),
        "history_item": (70, 70, 70),
    }
}

BUTTONS = [
    ["π", "%", "^", "√"],
    ["AC", "CE", "(", ")"],
    ["7", "8", "9", "×"],
    ["4", "5", "6", "÷"],
    ["1", "2", "3", "+"],
    [".", "0", "=", "-"]
]

class HistoryItem:
    def __init__(self, expression, result):
        self.expression = expression
        self.result = result
        self.timestamp = datetime.now()
    
    def __str__(self):
        return f"{self.expression} = {self.result}"

class Calculator:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Calculator")

        # UI elements
        self.display_rect = pygame.Rect(10, 60, WIDTH - 20, 100)
        self.history_button_rect = pygame.Rect(10, 10, 40, 40)
        self.theme_toggle_rect = pygame.Rect(60, 10, 40, 40)
        self.back_button_rect = pygame.Rect(10, 10, 70, 32)

        # Calculator state
        self.current_input = ""
        self.result_preview = ""
        self.cursor_pos = 0
        self.select_start = None
        self.select_end = None
        self.scroll_offset = 0
        self.mouse_selecting = False
        self.input_dragging_scrollbar = False
        self.input_drag_offset_y = 0

        # History state
        self.history_list = []
        self.history_scroll_offset = 0
        self.history_view_offset = WIDTH
        self.showing_history = False
        self.history_animation = 0
        self.history_dragging_scrollbar = False
        self.history_drag_offset_y = 0

        # Theme
        self.theme = "light"
        self.fonts = {
            "normal": pygame.font.SysFont("segoeui", 28),
            "large": pygame.font.SysFont("segoeui", 36),
            "small": pygame.font.SysFont("segoeuiemoji", 24),
            "history": pygame.font.SysFont("segoeui", 22),
            "symbols": pygame.font.SysFont("segoeuisymbol", 28),
        }

        # Create button rectangles
        self.button_rects = []
        for row_idx, row in enumerate(BUTTONS):
            for col_idx, label in enumerate(row):
                x = BUTTON_MARGIN + col_idx * (BUTTON_WIDTH + BUTTON_MARGIN)
                y = TOP_OFFSET + row_idx * (BUTTON_HEIGHT + BUTTON_MARGIN)
                rect = pygame.Rect(x, y, BUTTON_WIDTH, BUTTON_HEIGHT)
                self.button_rects.append((rect, label))

    def evaluate_expression(self, expr):
        try:
            # Input validation
            if len(expr) > 100:
                return "Input too long"
            if expr.count('(') != expr.count(')'):
                return "Unbalanced parentheses"
            if re.search(r'\d+\.\d+\.', expr):
                return "Invalid number"

            # Store original for history
            original_expr = expr
            
            # First handle square roots properly
            while '√' in expr:
                expr = re.sub(r'√\(([^)]+)\)', 
                             lambda m: str(math.sqrt(float(self.evaluate_simple_expression(m.group(1))))), 
                             expr)
                # Also handle square roots without parentheses for single numbers
                expr = re.sub(r'√(\d+\.?\d*)', 
                             lambda m: str(math.sqrt(float(m.group(1)))), 
                             expr)

            # Then handle parentheses recursively
            while '(' in expr:
                expr = re.sub(r'\(([^()]+)\)', 
                             lambda m: str(self.evaluate_simple_expression(m.group(1))), 
                             expr)

            # Then evaluate the remaining expression
            result = self.evaluate_simple_expression(expr)
            
            # Format result
            if abs(result) >= 1e8 or (0 < abs(result) < 1e-4 and result != 0):
                formatted = "{:.8e}".format(result)
            else:
                if isinstance(result, (int, float)) and result.is_integer():
                    formatted = str(int(result))
                else:
                    formatted = "{:.8f}".format(result).rstrip('0').rstrip('.')
                    if not formatted:
                        formatted = "0"
            
            # Add to history
            self.history_list.insert(0, HistoryItem(original_expr, formatted))
            return formatted
        except ValueError as e:
            if "math domain error" in str(e):
                return "Invalid sqrt input"
            return "Error"
        except ZeroDivisionError:
            return "Cannot divide by 0"
        except Exception as e:
            print(f"Error evaluating: {original_expr} - {str(e)}")
            return "Error"
                          
    def evaluate_simple_expression(self, expr):
        """Helper function to evaluate expressions without parentheses"""
        # Replace symbols
        expr = (expr.replace("×", "*").replace("÷", "/")
                   .replace("π", str(math.pi)).replace("^", "**"))
        
        # Handle square roots
        expr = re.sub(r'√(\d+(?:\.\d+)?)', r'math.sqrt(\1)', expr)
        
        # First evaluate all exponents
        while '**' in expr:
            expr = re.sub(r'(\d+\.?\d*)\s*\*\*\s*(\d+\.?\d*)', 
                         lambda m: str(float(m.group(1)) ** float(m.group(2))), 
                         expr)
        
        # Tokenize the remaining expression
        tokens = re.findall(r'(\d+\.?\d*%?|[\+\-\×\÷\*\/])', expr)
        
        # Initialize
        result = 0
        current_value = None
        last_operator = None
        
        for token in tokens:
            if token in '+-×÷*/':
                last_operator = token
                continue
                
            # Handle percentage
            if '%' in token:
                num = float(token.replace('%', '')) / 100
                if last_operator == '+':
                    current_value += current_value * num
                elif last_operator == '-':
                    current_value -= current_value * num
                elif last_operator in ('×', '*'):
                    current_value *= num
                elif last_operator in ('÷', '/'):
                    current_value /= num
                else:  # First term is a percentage
                    current_value = num
            else:
                # Regular number
                num = float(token)
                if current_value is None:
                    current_value = num
                else:
                    if last_operator == '+':
                        current_value += num
                    elif last_operator == '-':
                        current_value -= num
                    elif last_operator in ('×', '*'):
                        current_value *= num
                    elif last_operator in ('÷', '/'):
                        current_value /= num
        
        return current_value

    def wrap_text(self, text, max_chars):
        return [text[i:i+max_chars] for i in range(0, len(text), max_chars)] or [""]

    def get_selected_range(self):
        if self.select_start is None or self.select_end is None:
            return None, None
        return min(self.select_start, self.select_end), max(self.select_start, self.select_end)

    def get_cursor_position(self, lines):
        line_idx = self.cursor_pos // MAX_CHARS_PER_LINE
        char_idx = self.cursor_pos % MAX_CHARS_PER_LINE
        if line_idx < len(lines):
            x = self.fonts["large"].size(lines[line_idx][:char_idx])[0]
        else:
            x = 0
        y = line_idx * LINE_HEIGHT
        return x, y, line_idx

    def update_scroll_to_cursor(self, lines):
        line_idx = self.cursor_pos // MAX_CHARS_PER_LINE
        visible_lines = self.display_rect.height // LINE_HEIGHT

        if line_idx < self.scroll_offset:
            self.scroll_offset = line_idx
        elif line_idx >= self.scroll_offset + visible_lines:
            self.scroll_offset = max(0, line_idx - visible_lines + 1)

    def handle_input_event(self, event):
        lines = self.wrap_text(self.current_input, MAX_CHARS_PER_LINE)
        if self.result_preview:
            lines += self.wrap_text(f"= {self.result_preview}", MAX_CHARS_PER_LINE)

        if event.type == pygame.KEYDOWN:
            if (self.showing_history or self.history_animation != 0) and event.key == pygame.K_b:
                self.hide_history()
                return

            if event.key == pygame.K_c and pygame.key.get_mods() & pygame.KMOD_CTRL:
                sel_start, sel_end = self.get_selected_range()
                if sel_start is not None and sel_end is not None and sel_start != sel_end:
                    clipboard.copy(self.current_input[sel_start:sel_end])

            elif event.key == pygame.K_v and pygame.key.get_mods() & pygame.KMOD_CTRL:
                pasted = clipboard.paste()
                sel_start, sel_end = self.get_selected_range()
                if sel_start is not None and sel_end is not None:
                    self.current_input = self.current_input[:sel_start] + pasted + self.current_input[sel_end:]
                    self.cursor_pos = sel_start + len(pasted)
                else:
                    self.current_input = (self.current_input[:self.cursor_pos] + pasted +
                                         self.current_input[self.cursor_pos:])
                    self.cursor_pos += len(pasted)
                self.select_start = self.select_end = None

            elif event.key == pygame.K_BACKSPACE:
                sel_start, sel_end = self.get_selected_range()
                if sel_start is not None and sel_end is not None and sel_start != sel_end:
                    self.current_input = self.current_input[:sel_start] + self.current_input[sel_end:]
                    self.cursor_pos = sel_start
                    self.select_start = self.select_end = None
                elif self.cursor_pos > 0:
                    self.current_input = (self.current_input[:self.cursor_pos-1] +
                                         self.current_input[self.cursor_pos:])
                    self.cursor_pos -= 1

            elif event.key == pygame.K_RETURN or (hasattr(event, "unicode") and event.unicode == "="):
                if self.current_input:
                    result = self.evaluate_expression(self.current_input)
                    self.result_preview = result
                    self.cursor_pos = len(self.current_input)
                    self.select_start = self.select_end = None
                    self.scroll_offset = max(0, len(lines) - self.display_rect.height // LINE_HEIGHT + 1)

            elif hasattr(event, "unicode") and event.unicode.isprintable():
                if not (pygame.key.get_mods() & (pygame.KMOD_CTRL | pygame.KMOD_META)):
                    sel_start, sel_end = self.get_selected_range()
                    if sel_start is not None and sel_end is not None and sel_start != sel_end:
                        self.current_input = (self.current_input[:sel_start] + event.unicode +
                                             self.current_input[sel_end:])
                        self.cursor_pos = sel_start + 1
                    else:
                        self.current_input = (self.current_input[:self.cursor_pos] + event.unicode +
                                             self.current_input[self.cursor_pos:])
                        self.cursor_pos += 1
                    self.select_start = self.select_end = None

            elif event.key == pygame.K_LEFT:
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    if self.select_start is None:
                        self.select_start = self.cursor_pos
                    self.cursor_pos = max(0, self.cursor_pos - 1)
                    self.select_end = self.cursor_pos
                else:
                    self.cursor_pos = max(0, self.cursor_pos - 1)
                    self.select_start = self.select_end = None

            elif event.key == pygame.K_RIGHT:
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    if self.select_start is None:
                        self.select_start = self.cursor_pos
                    self.cursor_pos = min(len(self.current_input), self.cursor_pos + 1)
                    self.select_end = self.cursor_pos
                else:
                    self.cursor_pos = min(len(self.current_input), self.cursor_pos + 1)
                    self.select_start = self.select_end = None

            self.update_scroll_to_cursor(lines)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if not self.showing_history and self.display_rect.collidepoint(event.pos):
                self.handle_mouse_click(event.pos)
                
            if self.showing_history or self.history_animation != 0:
                thumb_rect = self.get_history_scrollbar_thumb_rect()
                if thumb_rect and thumb_rect.collidepoint(event.pos):
                    self.history_dragging_scrollbar = True
                    self.history_drag_offset_y = event.pos[1] - thumb_rect.y

            thumb_rect = self.get_scrollbar_thumb_rect(lines)
            if thumb_rect and thumb_rect.collidepoint(event.pos):
                self.input_dragging_scrollbar = True
                self.input_drag_offset_y = event.pos[1] - thumb_rect.y

            if not self.showing_history:
                for rect, label in self.button_rects:
                    if rect.collidepoint(event.pos):
                        self.handle_button_click(label)

            if self.showing_history or self.history_animation != 0:
                back_button_rect = pygame.Rect(
                    self.history_view_offset + 10,
                    10,
                    70,
                    32
                )
                if back_button_rect.collidepoint(event.pos):
                    self.hide_history()
                    return
                
                history_panel = pygame.Rect(self.history_view_offset + 10, 60, WIDTH - 20, HEIGHT - 70)
                y_offset = history_panel.y + 5
                for i, item in enumerate(self.history_list):
                    expr_lines = self.wrap_text(item.expression, MAX_CHARS_PER_LINE)
                    result_lines = self.wrap_text(f"= {item.result}", MAX_CHARS_PER_LINE)
                    item_height = (len(expr_lines) + len(result_lines)) * LINE_HEIGHT + HISTORY_ITEM_PADDING * 2
                    item_rect = pygame.Rect(
                        history_panel.x,
                        y_offset - self.history_scroll_offset,
                        history_panel.width,
                        item_height
                    )
                    if item_rect.collidepoint(event.pos):
                        self.current_input = item.expression
                        self.result_preview = item.result
                        self.cursor_pos = len(item.expression)
                        self.hide_history()
                        break
                    y_offset += item_height + 5

        elif event.type == pygame.MOUSEMOTION:
            if self.mouse_selecting and not self.showing_history:
                self.handle_mouse_selection(event.pos)
            if self.input_dragging_scrollbar and not self.showing_history:
                self.handle_scrollbar_drag(event.pos, lines)
            if self.history_dragging_scrollbar and (self.showing_history or self.history_animation != 0):
                self.handle_history_scrollbar_drag(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP:
            self.mouse_selecting = False
            self.input_dragging_scrollbar = False
            self.history_dragging_scrollbar = False
            
    def get_history_scrollbar_thumb_rect(self):
        if not self.history_list:
            return None
        
        total_height = 0
        for item in self.history_list:
            expr_lines = len(self.wrap_text(item.expression, MAX_CHARS_PER_LINE))
            result_lines = len(self.wrap_text(f"= {item.result}", MAX_CHARS_PER_LINE))
            total_height += (expr_lines + result_lines) * LINE_HEIGHT + HISTORY_ITEM_PADDING * 2 + 5
        
        visible_height = HEIGHT - 70
        
        if total_height <= visible_height:
            return None
        
        thumb_height = max(HISTORY_THUMB_MIN_HEIGHT, 
                          visible_height * (visible_height / total_height))
        
        max_scroll = total_height - visible_height
        thumb_y = 60 + (self.history_scroll_offset / max_scroll) * (visible_height - thumb_height)
        
        return pygame.Rect(
            WIDTH - HISTORY_SCROLLBAR_WIDTH - 5,
            thumb_y,
            HISTORY_SCROLLBAR_WIDTH,
            thumb_height
        )

    def handle_history_scrollbar_drag(self, pos):
        total_height = 0
        for item in self.history_list:
            expr_lines = len(self.wrap_text(item.expression, MAX_CHARS_PER_LINE))
            result_lines = len(self.wrap_text(f"= {item.result}", MAX_CHARS_PER_LINE))
            total_height += (expr_lines + result_lines) * LINE_HEIGHT + HISTORY_ITEM_PADDING * 2 + 5
        
        visible_height = HEIGHT - 70
        thumb_height = max(HISTORY_THUMB_MIN_HEIGHT, 
                          visible_height * (visible_height / total_height))
        max_scroll = max(1, total_height - visible_height)
        
        relative_y = pos[1] - 60 - self.history_drag_offset_y
        relative_y = max(0, min(relative_y, visible_height - thumb_height))
        self.history_scroll_offset = int((relative_y / (visible_height - thumb_height)) * max_scroll)

    def get_history_item_y_pos(self, index):
        y_pos = 0
        for i in range(index):
            expr_lines = len(self.wrap_text(self.history_list[i].expression, MAX_CHARS_PER_LINE))
            result_lines = len(self.wrap_text(f"= {self.history_list[i].result}", MAX_CHARS_PER_LINE))
            y_pos += (expr_lines + result_lines) * LINE_HEIGHT + HISTORY_ITEM_PADDING * 2 + 5
        return y_pos

    def handle_button_click(self, label):
        if label == "AC":
            self.current_input = ""
            self.result_preview = ""
            self.cursor_pos = 0
        elif label == "CE":
            if self.cursor_pos > 0:
                self.current_input = (self.current_input[:self.cursor_pos-1] +
                                     self.current_input[self.cursor_pos:])
                self.cursor_pos -= 1
        elif label == "=":
            if self.current_input:
                result = self.evaluate_expression(self.current_input)
                self.result_preview = result
                self.cursor_pos = len(self.current_input)
        elif label == "√":  # Modified square root button
            sel_start, sel_end = self.get_selected_range()
            if sel_start is not None and sel_end is not None:
                # Wrap selected text in √()
                self.current_input = (self.current_input[:sel_start] + "√(" +
                                     self.current_input[sel_start:sel_end] + ")" +
                                     self.current_input[sel_end:])
                self.cursor_pos = sel_start + len("√(") + (sel_end - sel_start) + 1
            else:
                # Insert √() and place cursor between parentheses
                self.current_input = (self.current_input[:self.cursor_pos] + "√()" +
                                     self.current_input[self.cursor_pos:])
                self.cursor_pos += 2  # Position cursor between parentheses
            self.select_start = self.select_end = None
        else:
            sel_start, sel_end = self.get_selected_range()
            if sel_start is not None and sel_end is not None:
                self.current_input = self.current_input[:sel_start] + label + self.current_input[sel_end:]
                self.cursor_pos = sel_start + len(label)
            else:
                self.current_input = self.current_input[:self.cursor_pos] + label + self.current_input[self.cursor_pos:]
                self.cursor_pos += len(label)
            self.select_start = self.select_end = None

    def handle_mouse_click(self, pos):
        rel_x = pos[0] - self.display_rect.x - 10
        rel_y = pos[1] - self.display_rect.y - 5
        line_idx = self.scroll_offset + rel_y // LINE_HEIGHT
        lines = self.wrap_text(self.current_input, MAX_CHARS_PER_LINE)
        char_idx = 0
        if line_idx < len(lines):
            text_line = lines[line_idx]
            for i in range(len(text_line)):
                char_x = self.fonts["large"].size(text_line[:i])[0]
                if rel_x < char_x + self.fonts["large"].size(text_line[i])[0] // 2:
                    break
                char_idx = i + 1
        self.cursor_pos = min(len(self.current_input), line_idx * MAX_CHARS_PER_LINE + char_idx)
        self.select_start = self.select_end = self.cursor_pos
        self.mouse_selecting = True

    def handle_mouse_selection(self, pos):
        rel_x = pos[0] - self.display_rect.x - 10
        rel_y = pos[1] - self.display_rect.y - 5
        line_idx = self.scroll_offset + rel_y // LINE_HEIGHT
        lines = self.wrap_text(self.current_input, MAX_CHARS_PER_LINE)
        char_idx = 0
        if line_idx < len(lines):
            text_line = lines[line_idx]
            for i in range(len(text_line)):
                char_x = self.fonts["large"].size(text_line[:i])[0]
                if rel_x < char_x + self.fonts["large"].size(text_line[i])[0] // 2:
                    break
                char_idx = i + 1
        self.cursor_pos = min(len(self.current_input), line_idx * MAX_CHARS_PER_LINE + char_idx)
        self.select_end = self.cursor_pos

    def handle_scrollbar_drag(self, pos, lines):
        scroll_area_height = self.display_rect.height
        content_height = len(lines) * LINE_HEIGHT
        thumb_height = max(20, scroll_area_height * (scroll_area_height / content_height))
        max_scroll = max(1, len(lines) - scroll_area_height // LINE_HEIGHT)
        relative_y = pos[1] - self.display_rect.y - self.input_drag_offset_y
        relative_y = max(0, min(relative_y, scroll_area_height - thumb_height))
        scroll_ratio = relative_y / (scroll_area_height - thumb_height)
        self.scroll_offset = int(scroll_ratio * max_scroll)

    def get_scrollbar_thumb_rect(self, lines):
        content_height = len(lines) * LINE_HEIGHT
        if content_height <= self.display_rect.height:
            return None
        scroll_area_height = self.display_rect.height
        thumb_height = max(20, scroll_area_height * (scroll_area_height / content_height))
        max_scroll = max(1, len(lines) - scroll_area_height // LINE_HEIGHT)
        thumb_y = (self.scroll_offset / max_scroll) * (scroll_area_height - thumb_height)
        return pygame.Rect(
            self.display_rect.right - 4,
            self.display_rect.y + thumb_y,
            4,
            thumb_height
        )

    def show_history(self):
        self.history_animation = 1

    def hide_history(self):
        self.history_animation = -1

    def update_history_animation(self):
        if self.history_animation == 1:
            self.history_view_offset = max(0, self.history_view_offset - ANIMATION_SPEED)
            if self.history_view_offset == 0:
                self.history_animation = 0
                self.showing_history = True
        elif self.history_animation == -1:
            self.history_view_offset = min(WIDTH, self.history_view_offset + ANIMATION_SPEED)
            if self.history_view_offset == WIDTH:
                self.history_animation = 0
                self.showing_history = False

    def draw_display(self):
        pygame.draw.rect(self.screen, THEMES[self.theme]["display"], self.display_rect, border_radius=12)
        lines = self.wrap_text(self.current_input, MAX_CHARS_PER_LINE)
        if self.result_preview:
            lines += self.wrap_text(f"= {self.result_preview}", MAX_CHARS_PER_LINE)
        self.screen.set_clip(self.display_rect)
        visible_lines = lines[self.scroll_offset:self.scroll_offset + self.display_rect.height // LINE_HEIGHT]
        for i, line in enumerate(visible_lines):
            y = self.display_rect.y + 5 + i * LINE_HEIGHT
            text_surface = self.fonts["large"].render(line, True, THEMES[self.theme]["text"])
            self.screen.blit(text_surface, (self.display_rect.x + 10, y))
        sel_start, sel_end = self.get_selected_range()
        if sel_start is not None and sel_end is not None and sel_start != sel_end:
            for idx in range(sel_start, sel_end):
                line_idx = idx // MAX_CHARS_PER_LINE
                char_idx = idx % MAX_CHARS_PER_LINE
                if (self.scroll_offset <= line_idx <
                    self.scroll_offset + self.display_rect.height // LINE_HEIGHT):
                    if line_idx < len(lines) and char_idx < len(lines[line_idx]):
                        text_before = lines[line_idx][:char_idx]
                        char = lines[line_idx][char_idx]
                        x_start = self.fonts["large"].size(text_before)[0]
                        char_width = self.fonts["large"].size(char)[0]
                        highlight_rect = pygame.Rect(
                            self.display_rect.x + 10 + x_start,
                            self.display_rect.y + 18 + (line_idx - self.scroll_offset) * LINE_HEIGHT,
                            char_width, LINE_HEIGHT - 7
                        )
                        pygame.draw.rect(self.screen, THEMES[self.theme]["selection"], highlight_rect)
                        char_surface = self.fonts["large"].render(char, True, THEMES[self.theme]["text"])
                        self.screen.blit(char_surface, (self.display_rect.x + 10 + x_start,
                                          self.display_rect.y + 5 + (line_idx - self.scroll_offset) * LINE_HEIGHT))
        x, y, line_idx = self.get_cursor_position(lines)
        if (self.scroll_offset <= line_idx <
            self.scroll_offset + self.display_rect.height // LINE_HEIGHT):
            pygame.draw.line(
                self.screen, THEMES[self.theme]["text"],
                (self.display_rect.x + 10 + x, self.display_rect.y + 18 + (line_idx - self.scroll_offset) * LINE_HEIGHT),
                (self.display_rect.x + 10 + x, self.display_rect.y + 9 + (line_idx - self.scroll_offset) * LINE_HEIGHT + LINE_HEIGHT),
                2
            )
        self.screen.set_clip(None)
        if len(lines) * LINE_HEIGHT > self.display_rect.height:
            thumb_rect = self.get_scrollbar_thumb_rect(lines)
            pygame.draw.rect(
                self.screen, THEMES[self.theme]["scrollbar"],
                (self.display_rect.right - 4, self.display_rect.top, 4, self.display_rect.height)
            )
            pygame.draw.rect(self.screen, THEMES[self.theme]["thumb"], thumb_rect)

    def draw_history_view(self):
        history_rect = pygame.Rect(self.history_view_offset, 0, WIDTH, HEIGHT)
        pygame.draw.rect(self.screen, THEMES[self.theme]["history_bg"], history_rect)
        
        back_button_rect = pygame.Rect(
            self.history_view_offset + 10,
            10,
            50,
            35
        )
        pygame.draw.rect(self.screen, THEMES[self.theme]["button"], back_button_rect, border_radius=6)
        back_txt = self.fonts["small"].render("⬅️", True, THEMES[self.theme]["text"])
        back_txt_rect = back_txt.get_rect(center=back_button_rect.center)
        self.screen.blit(back_txt, back_txt_rect)
        
        title_surface = self.fonts["normal"].render("History", True, THEMES[self.theme]["text"])
        self.screen.blit(title_surface, (self.history_view_offset + WIDTH//2 - title_surface.get_width()//2, 15))
        
        history_panel = pygame.Rect(self.history_view_offset + 10, 60, WIDTH - 20, HEIGHT - 70)
        self.screen.set_clip(history_panel)
        
        total_height = 0
        for item in self.history_list:
            expr_lines = len(self.wrap_text(item.expression, MAX_CHARS_PER_LINE))
            result_lines = len(self.wrap_text(f"= {item.result}", MAX_CHARS_PER_LINE))
            total_height += (expr_lines + result_lines) * LINE_HEIGHT + HISTORY_ITEM_PADDING * 2 + 5
        
        y_offset = history_panel.y + 5 - self.history_scroll_offset
        for item in self.history_list:
            expr_lines = self.wrap_text(item.expression, MAX_CHARS_PER_LINE)
            result_lines = self.wrap_text(f"= {item.result}", MAX_CHARS_PER_LINE)
            item_height = (len(expr_lines) + len(result_lines)) * LINE_HEIGHT + HISTORY_ITEM_PADDING * 2
            
            if y_offset + item_height > history_panel.y and y_offset < history_panel.bottom:
                item_rect = pygame.Rect(
                    history_panel.x,
                    y_offset,
                    history_panel.width - (HISTORY_SCROLLBAR_WIDTH + 5 if total_height > history_panel.height else 0),
                    item_height
                )
                pygame.draw.rect(self.screen, THEMES[self.theme]["history_item"], item_rect, border_radius=5)
                
                expr_y = item_rect.y + HISTORY_ITEM_PADDING
                for line in expr_lines:
                    expr_surface = self.fonts["history"].render(line, True, THEMES[self.theme]["text"])
                    self.screen.blit(expr_surface, (item_rect.x + 10, expr_y))
                    expr_y += LINE_HEIGHT
                
                result_y = expr_y
                for line in result_lines:
                    result_surface = self.fonts["history"].render(line, True, THEMES[self.theme]["text"])
                    self.screen.blit(result_surface, (item_rect.x + 10, result_y))
                    result_y += LINE_HEIGHT
            
            y_offset += item_height + 5
        
        self.screen.set_clip(None)
        
        if total_height > history_panel.height:
            pygame.draw.rect(
                self.screen, THEMES[self.theme]["scrollbar"],
                (self.history_view_offset + WIDTH - HISTORY_SCROLLBAR_WIDTH - 5, 
                 60, 
                 HISTORY_SCROLLBAR_WIDTH, 
                 history_panel.height)
            )
            
            thumb_rect = self.get_history_scrollbar_thumb_rect()
            if thumb_rect:
                pygame.draw.rect(
                    self.screen, THEMES[self.theme]["thumb"],
                    thumb_rect
                )

    def draw_buttons(self):
        for rect, label in self.button_rects:
            pygame.draw.rect(self.screen, THEMES[self.theme]["button"], rect, border_radius=12)
            text_surface = self.fonts["normal"].render(label, True, THEMES[self.theme]["text"])
            text_rect = text_surface.get_rect(center=rect.center)
            self.screen.blit(text_surface, text_rect)

    def draw_ui_elements(self):
        if not self.showing_history and self.history_animation == 0:
            pygame.draw.rect(self.screen, THEMES[self.theme]["button"], self.history_button_rect, border_radius=7)
            txt = self.fonts["small"].render("🕒", True, THEMES[self.theme]["text"])
            txt_rect = txt.get_rect(center=self.history_button_rect.center)
            self.screen.blit(txt, txt_rect)
            
            pygame.draw.rect(self.screen, THEMES[self.theme]["button"], self.theme_toggle_rect, border_radius=7)
            if self.theme == "light":
                ttxt = self.fonts["small"].render("🌙", True, THEMES[self.theme]["text"])
            elif self.theme == "dark":
                ttxt = self.fonts["small"].render("☀", True, THEMES[self.theme]["text"])
            ttxt_rect = ttxt.get_rect(center=self.theme_toggle_rect.center)
            self.screen.blit(ttxt, ttxt_rect)

    def run(self):
        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if not self.showing_history and self.theme_toggle_rect.collidepoint(event.pos):
                        self.theme = "dark" if self.theme == "light" else "light"
                    elif not self.showing_history and self.history_button_rect.collidepoint(event.pos):
                        self.show_history()

                if (self.showing_history or self.history_animation != 0) and event.type == pygame.MOUSEWHEEL:
                    self.history_scroll_offset -= event.y * 40
                    
                    total_height = 0
                    for item in self.history_list:
                        expr_lines = len(self.wrap_text(item.expression, MAX_CHARS_PER_LINE))
                        result_lines = len(self.wrap_text(f"= {item.result}", MAX_CHARS_PER_LINE))
                        total_height += (expr_lines + result_lines) * LINE_HEIGHT + HISTORY_ITEM_PADDING * 2 + 5
                    
                    max_scroll = max(0, total_height - (HEIGHT - 70))
                    self.history_scroll_offset = max(0, min(self.history_scroll_offset, max_scroll))
                    
                elif not self.showing_history and self.history_animation == 0:
                    if event.type == pygame.MOUSEWHEEL:
                        lines = self.wrap_text(self.current_input, MAX_CHARS_PER_LINE)
                        if self.result_preview:
                            lines += self.wrap_text(f"= {self.result_preview}", MAX_CHARS_PER_LINE)
                        max_scroll = max(0, len(lines) - self.display_rect.height // LINE_HEIGHT)
                        self.scroll_offset = max(0, min(self.scroll_offset - event.y, max_scroll))
                    self.handle_input_event(event)
                else:
                    self.handle_input_event(event)

            self.update_history_animation()
            self.screen.fill(THEMES[self.theme]["bg"])
            
            if not self.showing_history or self.history_view_offset > 0:
                self.draw_display()
                self.draw_buttons()
                self.draw_ui_elements()
            
            if self.showing_history or self.history_view_offset < WIDTH:
                self.draw_history_view()
            
            pygame.display.flip()
            clock.tick(60)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    calculator = Calculator()
    calculator.run()	