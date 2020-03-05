from square import get_square
import extend_2


def main():
    square = get_square()
    # This works, even though our extension is not in scope
    square.draw()


if __name__ == '__main__':
    main()
