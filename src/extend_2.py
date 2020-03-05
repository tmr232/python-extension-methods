from extend import monkey_extend as extend
from square import Square, draw_square


@extend(Square)
def draw(square):
    draw_square(square)