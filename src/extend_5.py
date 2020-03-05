from extend import extension
from square import Square, draw_square

@extension
class SquareExtensions(Square):
    def draw(self):
        draw_square(self)
