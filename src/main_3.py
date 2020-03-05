from square import get_square
# Now we have to bring the extension into our scope
from extend_3 import draw


def main():
    square = get_square()
    square.draw()

    # But __getattr__ fails
    try:
        print(square.snake)
    except AttributeError:
        print('__getattr__ is broken')


if __name__ == '__main__':
    main()
