from PIL import Image, ImageDraw, ImageFont
from draw_config import margin, white_cell_color, black_cell_color, sf_font


def to_str(checker):
    return to_str_format(checker % 10 - 1, checker // 10 - 1)


def to_str_format(row, col):
    return chr(ord('A') + row) + str(8 - col)


def square_place(up_left, down_right):
    return (margin - up_left, margin - up_left,
            margin + down_right, margin + down_right)


def cell_place(row, col):
    return (row * 64 + margin, col * 64 + margin,
            (row + 1) * 64 + margin, (col + 1) * 64 + margin)


def text_place(row, col, text, font):
    width, height = font.getsize(text)

    return (margin + row * 64 + (64 - width) // 2,
            margin + col * 64 + (64 - height) // 2 - 1)


def draw_blank_board():
    image = Image.new('RGB', (550, 550), white_cell_color)
    canvas = ImageDraw.Draw(image)

    canvas.rectangle(square_place(3, 515), fill=black_cell_color)
    canvas.rectangle(square_place(0, 512), fill=white_cell_color)

    font = ImageFont.truetype(*sf_font)

    for row in range(8):
        for col in range(8):
            if (row + col) % 2 == 1:
                canvas.rectangle(cell_place(row, col),
                                 fill=black_cell_color,
                                 outline=black_cell_color)

                text = to_str_format(row, col)
                canvas.text(text_place(row, col, text, font), text,
                            font=font, fill='white')

    image.save(fp='blank.png')


if __name__ == '__main__':
    draw_blank_board()
