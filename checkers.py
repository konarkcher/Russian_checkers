import copy
import random
import draw_config
from collections import namedtuple
from PIL import Image, ImageDraw, ImageFont

BoardLayout = namedtuple('BoardLayout', ['orient', 'layout'])


class Board:
    def __init__(self, enemy_white):
        self.enemy_white = enemy_white

        self._bot = BoardLayout(1, dict.fromkeys(
            [12, 14, 16, 18, 21, 23, 25, 27, 32, 34, 36, 38], False))
        self._enemy = BoardLayout(-1, dict.fromkeys(
            [61, 63, 65, 67, 72, 74, 76, 78, 81, 83, 85, 87], False))

    @staticmethod
    def make_move(pos, target, me, enemy):
        """Returns True if it was king's move"""
        y = me.orient if (target - pos) * me.orient > 0 else -me.orient
        x = 1 if target % 10 - pos % 10 > 0 else -1

        current_pos = pos + y * 10 + x
        while current_pos != target:
            if current_pos in enemy.layout:
                enemy.layout.pop(current_pos)

            current_pos = current_pos + y * 10 + x

        row = target // 10
        if (row, me.orient) in ((8, 1), (1, -1)):
            me.layout[target] = True
            me.layout.pop(pos)
        else:
            me.layout[target] = me.layout.pop(pos)

        if me.layout[target]:
            return True
        else:
            return False

    def move_options(self, target, bot):
        moves = {}
        compelled_board = False

        me, enemy = self.get_sides(bot)

        if target == -1:
            source = me.layout
        else:
            source = {target: me.layout[target]}

        for pos, is_king in source.items():
            if is_king:
                moves, compelled_board = self._add_options(
                    *self._king_options(pos, me, enemy), moves,
                    compelled_board)
            else:
                moves, compelled_board = self._add_options(
                    *self._men_options(pos, me, enemy), moves,
                    compelled_board)

        return moves, compelled_board

    def get_sides(self, bot):
        me, enemy = self._enemy, self._bot
        if bot:
            me, enemy = enemy, me

        return me, enemy

    def bot_score(self, bot):
        score = 0

        score += 4 * self._side_score(self._bot)
        score -= 3 * self._side_score(self._enemy)

        if bot:
            return score
        else:
            return -score

    def _side_score(self, me):
        score = 0

        for pos, is_king in me.layout.items():
            if is_king:
                score += 10
            else:
                score += 5
                if (pos // 10, me.orient) in ((1, 1), (8, -1)):
                    score += 2

            for cell in (pos - 11 * me.orient, pos - 9 * me.orient):
                if (cell in me.layout) or (not self._is_valid(cell)):
                    score += 1

        return score

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
    def _is_valid(pos):
        return 1 <= pos // 10 <= 8 and 1 <= pos % 10 <= 8

    @staticmethod
    def _free_cell(pos, me, enemy):
        return Board._is_valid(pos) and \
               (pos not in enemy.layout) and (pos not in me.layout)


def to_str(checker, enemy_white):
    return to_str_format(checker // 10 - 1, checker % 10 - 1, enemy_white)


def to_str_format(row, col, enemy_white):
    if enemy_white:
        row = 7 - row
        col = 7 - col

    return chr(ord('A') + 7 - col) + str(row + 1)


class Painter:
    def __init__(self):
        self._white_blank = self._draw_blank_board(enemy_white=True)
        self._black_blank = self._draw_blank_board(enemy_white=False)

    def _draw_blank_board(self, enemy_white):
        image = Image.new('RGB', (550, 550), draw_config.white_cell_color)
        canvas = ImageDraw.Draw(image)

        canvas.rectangle(self._square_place(3, 515),
                         fill=draw_config.black_cell_color)
        canvas.rectangle(self._square_place(0, 512),
                         fill=draw_config.white_cell_color)

        font = ImageFont.truetype(*draw_config.font)

        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1:
                    canvas.rectangle(self._cell_place(row, col),
                                     fill=draw_config.black_cell_color,
                                     outline=draw_config.black_cell_color)

                    text = to_str_format(row, col, enemy_white)
                    canvas.text(self._text_place(row, col, text, font, 'b'),
                                text, font=font, fill='white')

        return image

    def draw(self, board):
        if board.enemy_white:
            image = self._white_blank.copy()
        else:
            image = self._black_blank.copy()

        canvas = ImageDraw.Draw(image)

        enemy_palette = ('white', draw_config.black_draught_color,
                         draw_config.edge_color)
        bot_palette = ('black', draw_config.white_draught_color,
                       draw_config.edge_color)

        if board.enemy_white:
            enemy_palette, bot_palette = bot_palette, enemy_palette

        bot, enemy = board.get_sides(bot=True)

        self._draw_side(canvas, enemy.layout, enemy_palette, board.enemy_white)
        self._draw_side(canvas, bot.layout, bot_palette, board.enemy_white)

        image.save('tmp.png')

    def _draw_side(self, canvas, layout, palette, enemy_white):
        for checker, is_king in layout.items():
            if is_king:
                self._draw_checker(canvas, checker, *palette[:-1],
                                   draw_config.red_color, enemy_white)
            else:
                self._draw_checker(canvas, checker, *palette, enemy_white)

    def _draw_checker(self, canvas, checker, font_color, main_color,
                      other_color, enemy_white):

        row = checker // 10 - 1
        col = checker % 10 - 1

        canvas.ellipse(self._ellipse_place(row, col, 10, 5), fill=other_color)

        canvas.ellipse(self._ellipse_place(row, col, 5, 10),
                       fill=main_color, outline=other_color)

        font = ImageFont.truetype(*draw_config.font)
        text = to_str_format(row, col, enemy_white)
        canvas.text(self._text_place(row, col, text, font, 'c'), text,
                    font=font, fill=font_color)

    @staticmethod
    def _square_place(up_left, down_right):
        return (draw_config.margin - up_left, draw_config.margin - up_left,
                draw_config.margin + down_right,
                draw_config.margin + down_right)

    @staticmethod
    def _cell_place(row, col):
        return (col * 64 + draw_config.margin, row * 64 + draw_config.margin,
                (col + 1) * 64 + draw_config.margin,
                (row + 1) * 64 + draw_config.margin)

    @staticmethod
    def _ellipse_place(row, col, up_shift, down_shift):
        return (col * 64 + draw_config.margin + 5,
                row * 64 + draw_config.margin + up_shift,
                (col + 1) * 64 + draw_config.margin - 5,
                (row + 1) * 64 + draw_config.margin - down_shift)

    @staticmethod
    def _text_place(row, col, text, font, context):

        width, height = font.getsize(text)

        return (draw_config.margin + col * 64 + (64 - width) // 2,
                (draw_config.margin + row * 64 + 3 + (49 - height) // 2
                 if context == 'c' else
                 draw_config.margin + row * 64 + (64 - height) // 2 - 1))


class ArtificialIntelligence:
    def bot_move(self, board):
        moves, compelled_board = board.move_options(-1, bot=True)
        king_move = False
        if len(moves) == 0:
            return [], king_move

        moves_done = []

        first_move = True
        murder = -1
        while first_move or murder != -1:
            first_move = False

            score, best_moves = self._variant_score(board, depth=5, bot=True,
                                                    murder=murder)

            best_moves = self._remove_far(best_moves)

            pos, target = random.choice(best_moves)
            king_move = board.make_move(pos, target,
                                        *board.get_sides(bot=True))
            moves_done.append((to_str(pos, board.enemy_white),
                               to_str(target, board.enemy_white)))

            if compelled_board and board.move_options(target, bot=True)[1]:
                murder = target
            else:
                murder = -1

        return moves_done, king_move

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

    def _variant_score(self, board, depth, bot, murder):
        if depth == 0:
            return self._change_sign(board.bot_score(bot), murder), []

        best_score = -1000
        best_moves = []

        moves, compelled_board = board.move_options(murder, bot=bot)
        if len(moves) == 0:
            return self._change_sign(-1000, murder), []

        for pos, pos_options in moves.items():
            for target in pos_options:
                move_board = copy.deepcopy(board)
                move_board.make_move(pos, target, *move_board.get_sides(bot))

                if compelled_board and move_board.move_options(target,
                                                               bot=bot)[1]:
                    score, b_m = self._variant_score(move_board, depth - 1,
                                                     bot, target)
                else:
                    score, b_m = self._variant_score(move_board, depth - 1,
                                                     not bot, -1)

                if score > best_score:
                    best_score = score
                    best_moves = [(pos, target)]
                elif score == best_score:
                    best_moves.append((pos, target))

        return self._change_sign(best_score, murder), best_moves

    @staticmethod
    def _change_sign(score, murder):
        if murder == -1:
            return -score
        else:
            return score


class Game:
    painter = Painter()
    ai = ArtificialIntelligence()

    def __init__(self, enemy_white=True):
        self._board = Board(enemy_white=enemy_white)
        Game.painter.draw(self._board)

        self.murder = -1
        self.chosen_checker = -1
        self.until_draw = 15

    def black_first_move(self):
        moves_done, king_move = Game.ai.bot_move(self._board)
        self.update_draw(king_move)

        Game.painter.draw(self._board)
        return moves_done

    def button_variants(self):
        moves, c_b = self._board.move_options(-1, bot=False)
        if self.chosen_checker == -1:
            res = moves.keys()
        else:
            res = moves[self.chosen_checker]

        return [to_str(elem, self._board.enemy_white) for elem in list(res)]

    def external_session(self, ans):
        if ans not in self.button_variants():
            return (2 if self.chosen_checker == -1 else 1), []

        if self.chosen_checker == -1:
            self.chosen_checker = self._to_pos(ans, self._board.enemy_white)
            return 4, []
        else:
            return self.move_session(self.chosen_checker,
                                     self._to_pos(ans,
                                                  self._board.enemy_white))

    @staticmethod
    def _to_pos(ans, enemy_white):
        if enemy_white:
            return (9 - int(ans[1])) * 10 + (ord(ans[0]) - ord('A') + 1)
        else:
            return int(ans[1]) * 10 + (8 - ord(ans[0]) + ord('A'))

    def update_draw(self, king_move):
        if king_move:
            self.until_draw -= 1
        else:
            self.until_draw = 15

    def move_session(self, pos, target):  #
        """Returns 0 if you lose, 3 if choose checker, 4 if choose cell,
        5 if you win, 6 if choose target again, 7 if draw"""

        if self.murder == -1:
            moves, compelled_board = self._board.move_options(-1, bot=False)
        else:
            moves, compelled_board = self._board.move_options(self.murder,
                                                              bot=False)

        king_move = self._board.make_move(pos, target,
                                          *self._board.get_sides(bot=False))
        self.update_draw(king_move)

        if compelled_board and self._board.move_options(target, bot=False)[1]:
            self.murder = target
            self.chosen_checker = target
            Game.painter.draw(self._board)
            return 6, []
        else:
            self.murder = -1
            self.chosen_checker = -1

        moves_done, king_move = Game.ai.bot_move(self._board)
        self.update_draw(king_move)
        Game.painter.draw(self._board)

        if len(moves_done) == 0:
            return 5, moves_done

        moves, compelled_board = self._board.move_options(-1, bot=False)

        if len(moves) > 0:
            if self.until_draw > 0:
                return 3, moves_done
            else:
                return 7, moves_done
        else:
            return 0, moves_done
