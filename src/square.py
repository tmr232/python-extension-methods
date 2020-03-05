import itertools
from dataclasses import dataclass
from random import randint


@dataclass
class Square:
    length: int

    def __getattr__(self, name):
        if name == 'snake':
            return 'eyes'
        raise AttributeError()


def draw_square(square: Square):
    print('\n'.join(itertools.repeat('*' * square.length, square.length)))


def get_square():
        return Square(randint(1, 10))
