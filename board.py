import copy
import random
from collections import namedtuple
from PIL import Image, ImageDraw, ImageFont
from math import copysign
from draw_config import margin, sf_font, red_color, edge_color, \
    white_draught_color, black_draught_color


class Board:
    BoardLayout = namedtuple('BoardLayout', ['orient', 'layout'])

    def __init__(self, enemy_white=True):
        self._enemy_white = enemy_white

        self.murder = -1

        self._bot = self.BoardLayout(1, {  # True for king
            12: False, 14: False, 16: False, 18: False,
            21: False, 23: False, 25: False, 27: False,
            32: False, 34: False, 36: False, 38: False
        })
        self._enemy = self.BoardLayout(-1, {
            61: False, 63: False, 65: False, 67: False,
            72: False, 74: False, 76: False, 78: False,
            81: False, 83: False, 85: False, 87: False
        })

        if not enemy_white:
            self._bot_move()
        self._draw()
        # after init act like return 1

    def external_session(self, pos, target):
        """Returns -2 if you lose, -1 if wrong move, 0 if you have to
        capture, 1 if your turn, 2 if you win"""

        if self.murder == -1:
            moves, compelled_board = self._move_options(self._enemy, self._bot)
        else:
            moves, compelled_board = self._move_options(
                self._target_boardlayout(self._enemy, self.murder), self._bot)

        if not ((pos in moves) and (target in moves[pos])):
            return 0 if compelled_board else -1

        self._make_move(pos, target, self._enemy, self._bot)

        was_captured = compelled_board

        moves, compelled_board = self._move_options(
            self._target_boardlayout(self._enemy, target),
            self._bot)

        if was_captured and compelled_board:
            self.murder = target
            self._draw()
            return 0
        else:
            self.murder = -1

        moves_done = self._bot_move()
        if len(moves_done) == 0:
            return 2
        print(*moves_done)
        self._draw()

        moves, compelled_board = self._move_options(self._enemy, self._bot)

        if compelled_board:
            return 0
        elif len(moves) > 0:
            return 1
        else:
            return -2

    @staticmethod
    def _target_boardlayout(target_side, target):
        return Board.BoardLayout(target_side.orient,
                                 {target: target_side.layout[target]})

    def _bot_move(self):
        moves, compelled_board = self._move_options(self._bot, self._enemy)
        if len(moves) == 0:
            return []

        moves_done = []

        first_move = True
        was_captured = False
        while first_move or (compelled_board and was_captured):
            first_move = False

            score, best_moves = self._variant_score(depth=3, side=-1,
                                                    murder=-1)

            best_moves = self._remove_far(best_moves)

            pos, target = random.choice(best_moves)
            self._make_move(pos, target, self._bot, self._enemy)
            moves_done.append((pos, target))

            was_captured = compelled_board
            moves, compelled_board = self._move_options(
                self._target_boardlayout(self._bot, target), self._enemy)

        return moves_done

    @staticmethod
    def _remove_far(best_moves):
        new_list = []
        best_dist = 0

        for move in best_moves:
            row = move[1] // 10

            if row > best_dist:
                best_dist = row
                new_list = [move]
            elif row == best_dist:
                new_list.append(move)

        return new_list

    def _get_sides(self, side):
        me, enemy = self._bot, self._enemy
        if side == 1:
            me, enemy = enemy, me

        return me, enemy

    def _variant_score(self, depth, side, murder):  # side = -1 for bot
        if depth == 0:
            return copysign(self._score(*self._get_sides(side)), murder), []

        best_score = -1000
        best_moves = []

        if murder == -1:
            moves, compelled_board = self._move_options(*self._get_sides(side))
            if len(moves) == 0:
                return copysign(-1000, murder), []
        else:
            me, enemy = self._get_sides(side)
            moves, compelled_board = self._move_options(
                self._target_boardlayout(me, murder), enemy)

        for pos, pos_options in moves.items():
            for target in pos_options:
                move_board = copy.deepcopy(self)

                me, enemy = move_board._get_sides(side)
                move_board._make_move(pos, target, me, enemy)

                moves, compelled_board = move_board._move_options(
                    self._target_boardlayout(me, target), enemy)

                if compelled_board:
                    score, b_m = move_board._variant_score(depth - 1, side,
                                                           target)
                else:
                    score, b_m = move_board._variant_score(depth - 1, -side,
                                                           -1)

                if score > best_score:
                    best_score = score
                    best_moves = [(pos, target)]
                elif score == best_score:
                    best_moves.append((pos, target))

        return -best_score, best_moves

    def _side_score(self, me):
        score = 0

        for pos, is_king in me.layout.items():
            if is_king:
                score += 8
            else:
                score += 1
                if (pos // 10, me.orient) in [(1, 1), (8, -1)]:
                    score += 1

            for cell in [pos - 11 * me.orient, pos - 9 * me.orient]:
                if (cell in me.layout) or (not self._is_valid(cell)):
                    score += 1

        return score

    def _score(self, me, enemy):
        score = 0

        score += self._side_score(me)
        score -= self._side_score(enemy)

        return score

    @staticmethod
    def _make_move(pos, target, me, enemy):
        y = me.orient if (target - pos) * me.orient > 0 else -me.orient
        x = 1 if target % 10 - pos % 10 > 0 else -1

        current_pos = pos + y * 10 + x
        while current_pos != target:
            if current_pos in enemy.layout:
                enemy.layout.pop(current_pos)

            current_pos = current_pos + y * 10 + x

        row = target // 10
        if (row == 8 and me.orient == 1) or (row == 1 and me.orient == -1):
            me.layout[target] = True
            me.layout.pop(pos)
        else:
            me.layout[target] = me.layout.pop(pos)

    @staticmethod
    def _is_valid(pos):
        return 1 <= pos // 10 <= 8 and 1 <= pos % 10 <= 8

    @staticmethod
    def _free_cell(pos, me, enemy):
        return Board._is_valid(pos) and \
               (pos not in enemy.layout) and (pos not in me.layout)

    def _king_options(self, pos, me, enemy):
        pos_options = set()
        compelled_pos = False

        for direction in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            met_enemy = False
            opt = pos + 10 * direction[0] + direction[1]

            while self._is_valid(opt):
                if opt in enemy.layout:
                    if opt + 10 * direction[0] + direction[1] in enemy.layout:
                        break
                    met_enemy = True
                elif opt in me.layout:
                    break
                elif met_enemy == compelled_pos:
                    pos_options.add(opt)
                elif met_enemy:
                    compelled_pos = True
                    pos_options = {opt}

                opt += 10 * direction[0] + direction[1]

        return pos_options, pos, compelled_pos

    def _men_options(self, pos, me, enemy):
        pos_options = set()
        compelled_pos = False

        for opt in ((pos - 11 * me.orient, pos - 22 * me.orient),
                    (pos - 9 * me.orient, pos - 18 * me.orient),
                    (pos + 11 * me.orient, pos + 22 * me.orient),
                    (pos + 9 * me.orient, pos + 18 * me.orient)):

            if (opt[0] in enemy.layout) and self._free_cell(opt[1], me, enemy):
                if compelled_pos:
                    pos_options.add(opt[1])
                else:
                    compelled_pos = True
                    pos_options = {opt[1]}

            elif not compelled_pos and self._free_cell(opt[0], me, enemy) and \
                    ((opt[0] - pos) * me.orient > 0):
                pos_options.add(opt[0])

        return pos_options, pos, compelled_pos

    @staticmethod
    def _add_options(pos_options, pos, compelled_pos, moves,
                     compelled_board):
        if len(pos_options) > 0:
            if compelled_pos == compelled_board:
                moves[pos] = pos_options

            elif not compelled_board:
                compelled_board = True
                moves = {pos: pos_options}

        return moves, compelled_board

    def _move_options(self, me, enemy):
        moves = {}
        compelled_board = False

        for pos, is_king in me.layout.items():
            if is_king:
                moves, compelled_board = self._add_options(
                    *self._king_options(pos, me, enemy), moves,
                    compelled_board)
            else:
                moves, compelled_board = self._add_options(
                    *self._men_options(pos, me, enemy), moves,
                    compelled_board)

        return moves, compelled_board

    @staticmethod
    def _ellipse_place(row, col, up_shift, down_shift):
        return (row * 64 + margin + 5,
                col * 64 + margin + up_shift,
                (row + 1) * 64 + margin - 5,
                (col + 1) * 64 + margin - down_shift)

    @staticmethod
    def _text_place(row, col, text, font):

        width, height = font.getsize(text)

        return (margin + row * 64 + (64 - width) // 2,
                margin + col * 64 + 3 + (49 - height) // 2)

    @staticmethod
    def _draw_checker(canvas, checker, font_color, main_color, other_color):

        col = checker // 10 - 1
        row = checker % 10 - 1

        canvas.ellipse(Board._ellipse_place(row, col, 10, 5), fill=other_color)

        canvas.ellipse(Board._ellipse_place(row, col, 5, 10),
                       fill=main_color, outline=other_color)

        font = ImageFont.truetype(*sf_font)
        text = str((col + 1) * 10 + row + 1)
        canvas.text(Board._text_place(row, col, text, font), text,
                    font=font, fill=font_color)

    @staticmethod
    def _draw_side(canvas, layout, palette):
        for checker, is_king in layout.items():
            if is_king:
                Board._draw_checker(canvas, checker, *palette[:-1],
                                    red_color)
            else:
                Board._draw_checker(canvas, checker, *palette)

    def _draw(self):
        image = Image.open('blank.jpg')
        canvas = ImageDraw.Draw(image)

        enemy_palette = ('black', white_draught_color, edge_color)
        bot_palette = ('white', black_draught_color, edge_color)

        if not self._enemy_white:
            enemy_palette, bot_palette = bot_palette, enemy_palette

        self._draw_side(canvas, self._enemy.layout, enemy_palette)
        self._draw_side(canvas, self._bot.layout, bot_palette)

        image.show()


message = {
    -2: 'You lose :(', -1: 'Wrong move!', 0: 'You have to capture!',
    1: 'Your turn!', 2: 'You win!'
}

print('Would you like to play white? y/n : ', end='')
test_board = Board(enemy_white=(input() == 'y'))
res = 1
print(message[res])

while 1:
    inp = input().split()
    try:
        inp_pos, inp_target = int(inp[0]), int(inp[1])
    except:
        print(message[res])
        continue

    res = test_board.external_session(inp_pos, inp_target)
    print(message[res])

    if res in (-2, 2):
        break
