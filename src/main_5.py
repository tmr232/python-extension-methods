from square import get_square
# That's better. Far better.
# We're still stuck with the name, but it is far less likely
# to get overridden.
# Note that we cannot use `import x as y` here.
from extend_5 import SquareExtensions


def main():
    square = get_square()
    square.draw()


if __name__ == '__main__':
    main()
